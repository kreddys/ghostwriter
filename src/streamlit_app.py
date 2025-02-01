import os
import streamlit as st
import httpx
import asyncio
import logging
import logging.config
from dotenv import load_dotenv
from auth.authenticate import Authenticator

# Load environment variables
load_dotenv()

# Load logging configuration
logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)
logger.info("Streamlit app starting up")
logger.debug("Environment variables: %s", os.environ)

# Initialize authentication
allowed_users = os.getenv("ALLOWED_USERS").split(",")
authenticator = Authenticator(
    allowed_users=allowed_users,
    token_key=os.getenv("TOKEN_KEY"),
    secret_path="client_secret.json",
    redirect_uri=os.getenv("REDIRECT_URI", "http://localhost:8501")
)

# Hardcoded configuration
DEFAULT_CONFIG = {
    "search_engines": ["google", "tavily", "serp", "youtube"],
    "max_search_results": 2,
    "sites_list": None,  # None means search the entire web
    "search_days": 7,
    "slack_enabled": True,
    "slack_format_code_blocks": True,
    "use_query_generator": False,
    "use_url_filtering": False,
    "use_search_enricher": False,
    "similarity_threshold": 0.80,
    "relevance_similarity_threshold": 0.90,
    "scraping_engines": ["firecrawl", "youtube"],
    "topic": "Amaravati Capital City, Andhra Pradesh",
    "lightrag_timeout": 120.0,
    "chunk_size": 500,
    "chunk_overlap": 50,
}

# Configuration
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

async def call_fastapi(content: str, config: dict):
    """Call FastAPI endpoint with content and configuration"""
    timeout = httpx.Timeout(30.0)  # 30 seconds timeout
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        payload = {
            "input": {"messages": [{"role": "human", "content": content}]},
            "config": config
        }
        
        try:
            logger.info(f"Sending request to FastAPI: {FASTAPI_URL}/runs")
            async with client.stream(
                "POST",
                f"{FASTAPI_URL}/runs",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                
                # Create a container to display the streaming response
                response_container = st.empty()
                full_response = ""
                
                async for chunk in response.aiter_text():
                    if chunk:
                        full_response += chunk
                        response_container.text(full_response)
                
                logger.info("Request to FastAPI completed successfully")
                return {"response": full_response}
        except Exception as e:
            logger.error(f"Error calling FastAPI: {str(e)}")
            return {"error": str(e)}

def show_app_content():
    st.title("FastAPI Client with Configuration")
    
    # Create tabs for different sections
    tab1 = st.tabs(["Main Interface"])[0]
    
    with tab1:
        # Original app content
        content = st.text_area("Enter content", value="amaravati capital news")
        
        # Configuration options
        st.sidebar.title("Configuration")
    
    with st.sidebar.expander("Search Settings"):
        config = {
            "search_engines": st.multiselect(
                "Search Engines",
                options=["google", "tavily", "serp", "youtube"],
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
                logger.info("Starting request to FastAPI")
                result = asyncio.run(call_fastapi(content, config))
                if "error" in result:
                    logger.error(f"Error in FastAPI response: {result['error']}")
                    st.error(f"Error: {result['error']}")
                else:
                    logger.info("Request to FastAPI completed successfully")
                    st.success("Request successful!")
                    st.json(result)
            except Exception as e:
                logger.error(f"Error in Streamlit app: {str(e)}")
                st.error(f"Error: {str(e)}")

# Check authentication
authenticator.check_auth()
authenticator.login()

# Show app content only if authenticated
if st.session_state.get("connected"):
    logger.info(f"User {st.session_state['user_info'].get('email')} logged in")
    st.write(f"Welcome! {st.session_state['user_info'].get('email')}")
    if st.button("Log out"):
        logger.info("User logged out")
        authenticator.logout()
        st.rerun()
    
    show_app_content()
else:
    logger.info("User not authenticated")
    st.write("Please log in to access the application")

if __name__ == "__main__":
    pass
