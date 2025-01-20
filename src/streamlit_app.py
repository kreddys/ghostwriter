import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

# Load authentication config
with open('streamlit_auth_config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Login widget
name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status:
    authenticator.logout('Logout', 'main')
    st.write(f'Welcome *{name}*')
elif authentication_status is False:
    st.error('Username/password is incorrect')
elif authentication_status is None:
    st.warning('Please enter your username and password')

# Only show app content if authenticated
if not authentication_status:
    st.stop()

import httpx
import json
import asyncio
import logging
from datetime import datetime

# Default configuration values matching configuration.py
DEFAULT_CONFIG = {
    "system_prompt": "The system prompt to use for the agent's interactions",
    "model": "deepseek/deepseek-v3",
    "search_engines": ["tavily"],
    "max_search_results": 2,
    "sites_list": None,
    "search_days": 7,
    "slack_enabled": True,
    "slack_format_code_blocks": True,
    "use_query_generator": False,
    "use_url_filtering": False,
    "use_search_enricher": False,
    "similarity_threshold": 0.80,
    "relevance_similarity_threshold": 0.90
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
FASTAPI_URL = "http://fastapi-wrapper:8000"

async def call_fastapi(content: str, config: dict):
    """Call FastAPI endpoint with content and configuration"""
    timeout = httpx.Timeout(30.0)  # 30 seconds timeout
    
    # Log the complete configuration being sent
    logger.debug(f"Sending configuration: {json.dumps(config, indent=2)}")
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        payload = {
            "input": {"messages": [{"role": "human", "content": content}]},
            "config": config
        }
        
        logger.debug(f"Complete payload: {json.dumps(payload, indent=2)}")
        
        try:
            logger.debug(f"Sending request to FastAPI at {FASTAPI_URL}/runs")
            async with client.stream(
                "POST",
                f"{FASTAPI_URL}/runs",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                logger.debug(f"Received response: {response.status_code}")
                response.raise_for_status()
                
                # Create a container to display the streaming response
                response_container = st.empty()
                full_response = ""
                
                async for chunk in response.aiter_text():
                    if chunk:
                        try:
                            # Append each chunk to the full response
                            full_response += chunk
                            # Display the current response
                            response_container.text(full_response)
                        except Exception as e:
                            logger.error(f"Error processing chunk: {str(e)}")
                            return {"error": f"Error processing chunk: {str(e)}"}
                
                return {"response": full_response}
        except Exception as e:
            logger.error(f"Error calling FastAPI: {str(e)}")
            return {"error": str(e)}

def main():
    st.title("FastAPI Client with Configuration")
    
    # Content input
    content = st.text_area("Enter content", value="amaravati capital news")
    
    # Configuration options
    st.sidebar.title("Configuration")
    
    with st.sidebar.expander("Search Settings"):
        config = {
            "search_engines": st.multiselect(
                "Search Engines",
                options=["google", "tavily", "serp"],
                default=DEFAULT_CONFIG["search_engines"]
            ),
            "max_search_results": st.number_input(
                "Max Search Results",
                value=DEFAULT_CONFIG["max_search_results"],
                min_value=1
            ),
            "sites_list": st.text_area(
                "Sites List (comma separated)",
                value=",".join(DEFAULT_CONFIG["sites_list"]) if DEFAULT_CONFIG["sites_list"] else "",
                help="List of websites to search. Leave empty to search entire web"
            ),
            "search_days": st.selectbox(
                "Search Days",
                options=[1, 3, 7, 14, 30],
                index=2  # Default to 7 days
            )
        }
        # Convert sites_list from string to list
        config["sites_list"] = [s.strip() for s in config["sites_list"].split(",")] if config["sites_list"] else None
    
    with st.sidebar.expander("Content Settings"):
        config.update({
            "similarity_threshold": st.slider(
                "Similarity Threshold",
                min_value=0.0,
                max_value=1.0,
                value=DEFAULT_CONFIG["similarity_threshold"],
                help="Threshold for content uniqueness (lower = more strict)"
            ),
            "relevance_similarity_threshold": st.slider(
                "Relevance Threshold",
                min_value=0.0,
                max_value=1.0,
                value=DEFAULT_CONFIG["relevance_similarity_threshold"],
                help="Threshold for content relevance (higher = more strict)"
            )
        })
    
    with st.sidebar.expander("Integration Settings"):
        config.update({
            "slack_enabled": st.checkbox(
                "Enable Slack Integration",
                value=DEFAULT_CONFIG["slack_enabled"]
            ),
            "slack_format_code_blocks": st.checkbox(
                "Format Slack Messages as Code Blocks",
                value=DEFAULT_CONFIG["slack_format_code_blocks"]
            ),
            "use_query_generator": st.checkbox(
                "Use Query Generator",
                value=DEFAULT_CONFIG["use_query_generator"],
                help="Generate search queries from user input"
            ),
            "use_url_filtering": st.checkbox(
                "Use URL Filtering",
                value=DEFAULT_CONFIG["use_url_filtering"],
                help="Filter out URLs already in Supabase"
            ),
            "use_search_enricher": st.checkbox(
                "Use Search Enricher",
                value=DEFAULT_CONFIG["use_search_enricher"],
                help="Find additional relevant content"
            )
        })
    
    if st.button("Submit"):
        with st.spinner("Processing..."):
            try:
                result = asyncio.run(call_fastapi(content, config))
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.success("Request successful!")
                    st.json(result)
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
