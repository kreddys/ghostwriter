from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Union, List
import os
import logging
import json
from datetime import datetime
import uuid
from langgraph.pregel.remote import RemoteGraph

# Load logging configuration
import logging.config
logging.config.fileConfig("src/logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)

import sentry_sdk
try:
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        debug=False,
        traces_sample_rate=0.0,  # Disable tracing
        send_default_pii=True,
        auto_session_tracking=True,
        max_breadcrumbs=0,  # Disable breadcrumbs
    )
    logger.info("Sentry SDK initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Sentry SDK: {str(e)}", exc_info=True)

app = FastAPI()
logger.info("FastAPI app starting up")
logger.debug("Environment variables: %s", os.environ)

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
        # Log incoming request details
        logger.debug(f"Received request with config: {request.config}")
        if request.config and "search_engines" in request.config:
            logger.info(f"Configured search engines: {request.config['search_engines']}")
        
        # Initialize RemoteGraph client
        langgraph_client = RemoteGraph(
            "agent",  # name as positional argument
            url=os.getenv("LANGGRAPH_API_URL"),
            api_key=os.getenv("LANGSMITH_API_KEY")
        )

        # Stream the response back to the client
        async def generate():
            try:
                # Prepare LangGraph config with proper structure
                langgraph_config = {
                    "configurable": {
                        "thread_id": str(uuid.uuid4()),
                        # Model configurations
                        "llm_model": request.config.get("llm_model", "google/gemini-2.0-flash-lite-preview-02-05:free"),
                        "embedding_model": request.config.get("embedding_model", "multilingual-e5-large"),
                        
                        # Search configurations
                        "search_engines": request.config.get("search_engines", ["google", "tavily", "serp", "youtube"]),
                        "max_search_results": request.config.get("max_search_results", 5),
                        "sites_list": request.config.get("sites_list"),
                        "search_days": request.config.get("search_days", 7),
                        
                        # Similarity thresholds
                        "similarity_threshold": request.config.get("similarity_threshold", 0.85),
                        "relevance_similarity_threshold": request.config.get("relevance_similarity_threshold", 0.90),
                        
                        # Integration settings
                        "slack_enabled": request.config.get("slack_enabled", True),
                        "slack_format_code_blocks": request.config.get("slack_format_code_blocks", True),
                        "use_query_generator": request.config.get("use_query_generator", False),
                        "use_url_filtering": request.config.get("use_url_filtering", False),
                        
                        # Scraping and processing settings
                        "scraping_engines": request.config.get("scraping_engines", ["firecrawl", "youtube"]),
                        "topic": request.config.get("topic", "Amaravati Capital City, Andhra Pradesh"),
                        "skip_uniqueness_checker": request.config.get("skip_uniqueness_checker", True),
                    }
                }
                
                logger.debug(f"Prepared LangGraph config: {json.dumps(langgraph_config, indent=2)}")
                
                # Use astream with proper streaming configuration
                stream = langgraph_client.astream(
                    input=request.input,
                    config=langgraph_config,
                    stream_mode=["updates"],
                    on_disconnect="continue"
                )
                
                async for chunk in stream:
                    logger.debug(f"Processing chunk: {chunk}")
                    try:
                        if chunk:
                            if isinstance(chunk, dict):
                                response_data = json.dumps(chunk)
                                logger.debug(f"Yielding JSON chunk: {response_data}")
                                yield response_data + "\n"
                            else:
                                logger.debug(f"Yielding string chunk: {str(chunk)}")
                                yield str(chunk) + "\n"
                        else:
                            logger.warning("Received empty chunk from LangGraph")
                            warning_msg = json.dumps({
                                "status": "warning",
                                "message": "Empty response chunk",
                                "timestamp": str(datetime.now())
                            })
                            logger.debug(f"Yielding warning: {warning_msg}")
                            yield warning_msg + "\n"
                    except Exception as e:
                        logger.error(f"Error processing chunk: {str(e)}", exc_info=True)
                        error_msg = json.dumps({
                            "status": "error",
                            "message": f"Chunk processing error: {str(e)}",
                            "timestamp": str(datetime.now())
                        })
                        yield error_msg + "\n"
                        
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

# Determine the host based on the environment
host = "0.0.0.0" if os.getenv("FLY_APP_NAME") else "localhost"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=host, port=8000)
