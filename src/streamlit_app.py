import streamlit as st
import httpx
import json
import os
import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://fastapi-wrapper:8000")

async def create_assistant(graph_id: str, graph_name: str) -> Optional[Dict[str, Any]]:
    """Create a new assistant"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{FASTAPI_URL}/assistants",
                json={
                    "graph_id": graph_id,
                    "name": graph_name
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            st.error(f"Failed to create assistant: {str(e)}")
            return None

async def create_thread(assistant_id: str) -> Optional[Dict[str, Any]]:
    """Create a new thread"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{FASTAPI_URL}/threads",
                json={"assistant_id": assistant_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            st.error(f"Failed to create thread: {str(e)}")
            return None

async def stream_run(
    thread_id: str,
    assistant_id: str,
    content: str,
    config: dict,
    metadata: dict = {},
    tags: list[str] = [],
    recursion_limit: int = 10,
    stream_mode: list[str] = ["updates"],
    stream_subgraphs: bool = False,
    on_disconnect: str = "cancel",
    webhook: str | None = None
) -> AsyncGenerator[str, None]:
    """Stream run response"""

    timeout =     timeout = httpx.Timeout(
        timeout=300.0,  # 5 minutes total timeout
        connect=30.0,   # 30 seconds connect timeout
        read=None      # No read timeout for streaming
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        payload = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "input": {"messages": [{"role": "human", "content": content}]},
            "config": {
                **config,
                "recursion_limit": recursion_limit,
                "stream_mode": stream_mode,
                "stream_subgraphs": stream_subgraphs,
                "on_disconnect": on_disconnect
            },
            "metadata": metadata,
            "tags": tags,
            "webhook": webhook
        }
        
        try:
            async with client.stream(
                "POST",
                f"{FASTAPI_URL}/runs",
                json=payload,
                headers={
                    "Accept": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            ) as response:
                response.raise_for_status()
                logger.info(f"Stream started with status: {response.status_code}")
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        logger.debug(f"Received chunk: {chunk}")
                        yield chunk
                    else:
                        # Send keep-alive
                        yield json.dumps({
                            "status": "keepalive",
                            "timestamp": str(datetime.now())
                        })
        except httpx.StreamClosed as e:
            logger.warning(f"Stream closed: {str(e)}")
            yield json.dumps({
                "status": "error",
                "message": "Stream closed unexpectedly",
                "timestamp": str(datetime.now())
            })
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield json.dumps({
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            })

def main():
    st.title("LangGraph Workflow")
    
    # Initialize session state
    if "assistant" not in st.session_state:
        st.session_state.assistant = None
    if "thread" not in st.session_state:
        st.session_state.thread = None
    if "running" not in st.session_state:
        st.session_state.running = False
    
    with st.form("workflow_form"):
        # Basic configuration
        col1, col2 = st.columns(2)
        with col1:
            graph_id = st.text_input("Graph ID", value="agent")
            graph_name = st.text_input("Graph Name", value="react-agent")
            content = st.text_area("Content", value="amaravati capital news")
            
        with col2:
            recursion_limit = st.number_input("Recursion Limit", value=10, min_value=1)
            stream_mode = st.multiselect(
                "Stream Mode",
                options=["values", "messages", "messages-tuple", "updates", "events", "debug", "custom"],
                default=["updates"]
            )
            stream_subgraphs = st.checkbox("Stream Subgraphs", value=False)
            on_disconnect = st.selectbox(
                "On Disconnect",
                options=["cancel", "continue"],
                index=0
            )
            
        # Agent Configuration
        with st.expander("Agent Configuration"):
            st.markdown("### Search Settings")
            col3, col4 = st.columns(2)
            with col3:
                search_engines = st.multiselect(
                    "Search Engines",
                    options=["google", "tavily", "serp"],
                    default=["google", "tavily", "serp"],
                    help="List of search engines to use"
                )
                max_search_results = st.number_input(
                    "Max Search Results",
                    value=2,
                    min_value=1,
                    help="Maximum number of search results per query"
                )
                search_days = st.number_input(
                    "Search Days",
                    value=7,
                    min_value=1,
                    help="Number of days to look back for search results"
                )
                
            with col4:
                sites_list = st.text_area(
                    "Sites List",
                    value="",
                    help="List of websites to search (one per line)"
                )
                use_query_generator = st.checkbox(
                    "Use Query Generator",
                    value=False,
                    help="Generate search queries from user input"
                )
                use_url_filtering = st.checkbox(
                    "Use URL Filtering",
                    value=False,
                    help="Filter out URLs that exist in Supabase"
                )
                
            st.markdown("### Content Settings")
            col5, col6 = st.columns(2)
            with col5:
                similarity_threshold = st.slider(
                    "Similarity Threshold",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.80,
                    help="Threshold for content uniqueness (lower = more strict)"
                )
                relevance_similarity_threshold = st.slider(
                    "Relevance Threshold",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.90,
                    help="Threshold for content relevance (higher = more strict)"
                )
                
            st.markdown("### Slack Settings")
            col7, col8 = st.columns(2)
            with col7:
                slack_enabled = st.checkbox(
                    "Slack Enabled",
                    value=True,
                    help="Enable Slack integration"
                )
                slack_format_code_blocks = st.checkbox(
                    "Format Code Blocks",
                    value=True,
                    help="Format articles as code blocks in Slack"
                )
                
        submitted = st.form_submit_button("Start Workflow")
    
    if submitted and not st.session_state.running:
        st.session_state.running = True
        
        # Create assistant
        with st.spinner("Creating assistant..."):
            assistant = asyncio.run(create_assistant(graph_id, graph_name))
            if assistant and "assistant_id" in assistant:
                st.session_state.assistant = assistant
                st.success(f"Assistant created: {assistant['assistant_id']}")
            elif assistant:
                st.error("Invalid assistant response format")
                st.json(assistant)
                return None
        
        # Create thread
        if st.session_state.assistant:
            with st.spinner("Creating thread..."):
                thread = asyncio.run(create_thread(st.session_state.assistant["assistant_id"]))
                if thread and "thread_id" in thread:
                    st.session_state.thread = thread
                    st.success(f"Thread created: {thread['thread_id']}")
                elif thread:
                    st.error("Invalid thread response format")
                    st.json(thread)
                    return None
        
        # Start streaming
        if st.session_state.assistant and st.session_state.thread:
            st.write("Streaming response:")
            response_container = st.empty()
            full_response = ""
            
            async def process_stream():
                nonlocal full_response
                try:
                    # Prepare config from form inputs
                    config = {
                        "search_engines": search_engines,
                        "max_search_results": max_search_results,
                        "search_days": search_days,
                        "sites_list": [s.strip() for s in sites_list.split("\n") if s.strip()],
                        "use_query_generator": use_query_generator,
                        "use_url_filtering": use_url_filtering,
                        "similarity_threshold": similarity_threshold,
                        "relevance_similarity_threshold": relevance_similarity_threshold,
                        "slack_enabled": slack_enabled,
                        "slack_format_code_blocks": slack_format_code_blocks
                    }
                    
                    # Initialize connection state
                    last_received = datetime.now()
                    keepalive_interval = 30  # seconds
                    max_idle_time = 300  # seconds
                    
                    async for chunk in stream_run(
                        st.session_state.thread["thread_id"],
                        st.session_state.assistant["assistant_id"],
                        content,
                        config=config,
                        recursion_limit=recursion_limit,
                        stream_mode=stream_mode,
                        stream_subgraphs=stream_subgraphs,
                        on_disconnect=on_disconnect
                    ):
                        if chunk:
                            try:
                                data = json.loads(chunk)
                                if isinstance(data, dict):
                                    if data.get("status") == "stream_closed":
                                        st.warning("Stream closed by server")
                                        break
                                    if data.get("status") == "error":
                                        st.error(data.get("message", "Unknown error"))
                                        break
                                    if data.get("status") == "keepalive":
                                        # Update last received time but don't display
                                        last_received = datetime.now()
                                        continue
                                    elif data.get("status") == "completed":
                                        logger.info("Stream completed successfully")
                                        break
                                        
                                # Update last received time and display content
                                last_received = datetime.now()
                                full_response += chunk + "\n"
                                response_container.markdown(f"```\n{full_response}\n```")
                                
                                # Check for idle timeout
                                idle_time = (datetime.now() - last_received).total_seconds()
                                if idle_time > max_idle_time:
                                    st.warning(f"Connection idle for {int(idle_time)} seconds, closing")
                                    break
                                    
                            except json.JSONDecodeError:
                                # Handle raw text chunks
                                last_received = datetime.now()
                                full_response += chunk + "\n"
                                response_container.markdown(f"```\n{full_response}\n```")
                                
                except Exception as e:
                    st.error(f"Error during streaming: {str(e)}")
                    logger.error(f"Stream error: {str(e)}", exc_info=True)
            
            try:
                asyncio.run(process_stream())
            finally:
                st.session_state.running = False

if __name__ == "__main__":
    main()
