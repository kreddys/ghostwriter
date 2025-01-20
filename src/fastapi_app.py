from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Union
import httpx
import os
import logging
import json
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

# Configure timeouts (30 minutes for long operations)
TIMEOUT = httpx.Timeout(1800.0, connect=60.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create a persistent HTTP client
    app.state.client = httpx.AsyncClient(timeout=TIMEOUT)
    yield
    # Clean up the client
    await app.state.client.aclose()

app = FastAPI(lifespan=lifespan)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# Enable debug logging for httpx
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)

LANGGRAPH_API_URL = os.getenv("LANGGRAPH_API_URL")

class AssistantCreateRequest(BaseModel):
    graph_id: str
    name: str = "react-agent"
    config: dict = {}
    metadata: dict = {}

class ThreadCreateRequest(BaseModel):
    assistant_id: str

class RunCreateRequest(BaseModel):
    thread_id: str
    assistant_id: str
    input: dict
    config: dict
    metadata: dict = {}
    tags: list[str] = []
    recursion_limit: int = 10
    stream_mode: list[str] = ["updates"]
    stream_subgraphs: bool = False
    on_disconnect: str = "cancel"

@app.post("/assistants")
async def create_assistant(request: AssistantCreateRequest):
    try:
        response = await app.state.client.post(
            f"{LANGGRAPH_API_URL}/assistants",
            json={
                "graph_id": request.graph_id,
                "name": request.name,
                "config": request.config,
                "metadata": request.metadata
            },
            headers={"Authorization": f"Bearer {os.getenv('LANGSMITH_API_KEY')}"}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Assistant creation failed: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

@app.post("/threads")
async def create_thread(request: ThreadCreateRequest):
    try:
        response = await app.state.client.post(
            f"{LANGGRAPH_API_URL}/threads",
            json={"assistant_id": request.assistant_id},
            headers={"Authorization": f"Bearer {os.getenv('LANGSMITH_API_KEY')}"}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Thread creation failed: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

@app.post("/runs")
async def create_run(request: RunCreateRequest):
    """Create and stream a new run for a thread."""
    try:
        # Prepare the request body according to LangGraph API requirements
        request_body = {
            "thread_id": request.thread_id,
            "assistant_id": request.assistant_id,
            "input": request.input,
            "config": {
                **request.config,
                "recursion_limit": request.recursion_limit,
                "stream_mode": request.stream_mode,
                "stream_subgraphs": request.stream_subgraphs,
                "on_disconnect": request.on_disconnect
            },
            "metadata": request.metadata,
            "tags": request.tags
        }
        
        logger.info(f"Sending request to LangGraph API: {request_body}")
        
        # Use streaming response to handle long-running operations
        async with app.state.client.stream(
            "POST",
            f"{LANGGRAPH_API_URL}/threads/{request.thread_id}/runs/stream",
            json=request_body,
            headers={"Authorization": f"Bearer {os.getenv('LANGSMITH_API_KEY')}"}
        ) as response:
            response.raise_for_status()
            
            # Stream the response back to the client
            async def generate():
                try:
                    logger.info("Starting stream...")
                    logger.debug(f"Stream headers: {response.headers}")
                    logger.debug(f"Stream status: {response.status_code}")

                    async for chunk in response.aiter_text():
                        if chunk.strip():  # Only yield non-empty chunks
                            logger.debug(f"Received chunk: {chunk}")
                            yield chunk

                except httpx.StreamClosed as e:
                    logger.warning(f"Stream closed by client - connection terminated. Details: {str(e)}")
                    logger.debug(f"Response status: {response.status_code}")
                    logger.debug(f"Response headers: {response.headers}")
                    closed_msg = json.dumps({
                        "status": "stream_closed",
                        "message": "Client disconnected",
                        "timestamp": str(datetime.now())
                    })
                    logger.debug(f"Sending stream closed: {closed_msg}")
                    yield closed_msg
                            
                except Exception as e:
                    logger.error(f"Stream error: {str(e)}", exc_info=True)
                    error_msg = json.dumps({
                        "status": "error",
                        "message": str(e),
                        "timestamp": str(datetime.now())
                    })
                    logger.debug(f"Sending error: {error_msg}")
                    yield error_msg
                            
                finally:
                    try:
                        # Ensure the response is properly closed
                        await response.aclose()
                        logger.debug("Stream response closed successfully")
                    except Exception as e:
                        logger.error(f"Error closing stream response: {str(e)}")
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "X-Accel-Buffering": "no",  # Disable buffering for nginx
                    "Cache-Control": "no-store",
                    "Connection": "keep-alive",
                }
            )
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Run creation failed: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/debug")
async def debug_info():
    """Debug endpoint to show current configuration"""
    return {
        "langgraph_api_url": LANGGRAPH_API_URL,
        "logging_level": logging.getLevelName(logger.getEffectiveLevel()),
        "timeout": str(TIMEOUT)
    }

@app.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    try:
        response = await app.state.client.get(
            f"{LANGGRAPH_API_URL}/runs/{run_id}",
            headers={"Authorization": f"Bearer {os.getenv('LANGSMITH_API_KEY')}"}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Run status check failed: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
