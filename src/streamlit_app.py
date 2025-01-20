import streamlit as st
import httpx
import json
import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
FASTAPI_URL = "http://fastapi-wrapper:8000"

async def call_fastapi(content: str):
    """Call FastAPI endpoint with content"""
    timeout = httpx.Timeout(30.0)  # 30 seconds timeout
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        payload = {
            "input": {"messages": [{"role": "human", "content": content}]},
            "config": {}  # Empty config for now
        }
        
        try:
            logger.debug(f"Sending request to FastAPI at {FASTAPI_URL}/runs")
            response = await client.post(
                f"{FASTAPI_URL}/runs",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            logger.debug(f"Received response: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error calling FastAPI: {str(e)}")
            return {"error": str(e)}

def main():
    st.title("Simple FastAPI Client")
    
    content = st.text_area("Enter content", value="amaravati capital news")
    
    if st.button("Submit"):
        with st.spinner("Processing..."):
            try:
                result = asyncio.run(call_fastapi(content))
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.success("Request successful!")
                    st.json(result)
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
