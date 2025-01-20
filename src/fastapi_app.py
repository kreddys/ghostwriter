from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Union, List
import os
import logging
import json
from datetime import datetime
from langgraph.pregel.remote import RemoteGraph

app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

class RunCreateRequest(BaseModel):
    input: dict
    config: Optional[dict] = None
    stream_mode: Optional[Union[str, List[str]]] = None
    stream_subgraphs: Optional[bool] = None
    on_disconnect: Optional[str] = None

@app.post("/runs")
async def create_run(request: RunCreateRequest):
    """Create and stream a new run using LangGraph SDK."""
    try:
        # Initialize RemoteGraph client
        langgraph_client = RemoteGraph(
            "agent",  # name as positional argument
            url=os.getenv("LANGGRAPH_API_URL"),
            api_key=os.getenv("LANGSMITH_API_KEY")
        )

        # Stream the response back to the client
        async def generate():
            try:
                async for chunk in langgraph_client.astream(
                    input=request.input,
                    config=request.config or {},
                    stream_mode=request.stream_mode,
                    on_disconnect=request.on_disconnect
                ):
                    if isinstance(chunk, dict):
                        yield json.dumps(chunk) + "\n"
                    else:
                        yield str(chunk) + "\n"
                        
            except Exception as e:
                logger.error(f"Stream error: {str(e)}", exc_info=True)
                error_msg = json.dumps({
                    "status": "error",
                    "message": str(e),
                    "timestamp": str(datetime.now())
                })
                yield error_msg + "\n"
            
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-store",
                "Connection": "keep-alive"
            }
        )
            
    except Exception as e:
        logger.error(f"Run creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
