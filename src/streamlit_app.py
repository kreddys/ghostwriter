import streamlit as st
import httpx
import json
import os
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any

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

async def stream_run(thread_id: str, assistant_id: str, content: str) -> AsyncGenerator[str, None]:
    """Stream run response"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "content": content,
            "stream_mode": "updates"
        }
        
        async with client.stream(
            "POST",
            f"{FASTAPI_URL}/runs",
            json=payload
        ) as response:
            async for chunk in response.aiter_text():
                if chunk.strip():
                    yield chunk

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
        graph_id = st.text_input("Graph ID", value="agent")
        graph_name = st.text_input("Graph Name", value="react-agent")
        content = st.text_area("Content", value="amaravati capital news")
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
                    async for chunk in stream_run(
                        st.session_state.thread["thread_id"],
                        st.session_state.assistant["assistant_id"],
                        content
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
                                full_response += chunk
                                response_container.markdown(f"```\n{full_response}\n```")
                            except json.JSONDecodeError:
                                full_response += chunk
                                response_container.markdown(f"```\n{full_response}\n```")
                except Exception as e:
                    st.error(f"Error during streaming: {str(e)}")
            
            try:
                asyncio.run(process_stream())
            finally:
                st.session_state.running = False

if __name__ == "__main__":
    main()
