import os
import streamlit as st
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.tracing import start_transaction

# Initialize Sentry
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),  # Use the Sentry DSN from the .env file
    integrations=[LoggingIntegration()],
    traces_sample_rate=1.0,  # Capture 100% of transactions for performance monitoring
    send_default_pii=True,  # Automatically capture personally identifiable information
)

# Function to add breadcrumbs
def add_breadcrumb(category, message, level="info"):
    sentry_sdk.add_breadcrumb(
        category=category,
        message=message,
        level=level
    )
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
    "llm_model": "google/gemini-2.0-flash-lite-preview-02-05:free",  # Added
    "embedding_model": "multilingual-e5-large",  # Added
    "search_engines": ["google", "tavily", "serp", "youtube"],
    "max_search_results": 2,
    "sites_list": None,
    "search_days": 7,
    "slack_enabled": True,
    "slack_format_code_blocks": True,
    "use_query_generator": False,
    "use_url_filtering": False,
    "similarity_threshold": 0.85,  # Updated to match configuration.py
    "relevance_similarity_threshold": 0.90,
    "scraping_engines": ["firecrawl", "youtube"],
    "topic": "Amaravati Capital City, Andhra Pradesh",
    "skip_uniqueness_checker": True,  # Added
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
        content = st.text_area("Enter content", value="amaravati capital news")
        
        st.sidebar.title("Configuration")
    
    # Add new Model Settings expander
    with st.sidebar.expander("Model Settings"):
        config = {
            "llm_model": st.selectbox(
                "LLM Model",
                options=[
                    "google/gemini-2.0-flash-lite-preview-02-05:free",
                    "google/gemini-flash-1.5",
                    "google/gemini-2.0-flash-001",
                    "openai/o1-mini",
                    "openai/gpt-4o-mini",
                    "meta-llama/llama-3.3-70b-instruct",
                    "deepseek/deepseek-r1:free"
                ],
                default=DEFAULT_CONFIG["llm_model"],
                help="Select the Language Model to use"
            ),
            "embedding_model": st.selectbox(
                "Embedding Model",
                options=[
                    "multilingual-e5-large",
                    "text-embedding-ada-002"
                ],
                default=DEFAULT_CONFIG["embedding_model"],
                help="Select the Embedding Model to use"
            )
        }
    
    with st.sidebar.expander("Search Settings"):
        config.update({
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
                index=2
            )
        })
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
            ),
            "skip_uniqueness_checker": st.checkbox(
                "Skip Uniqueness Checker",
                value=DEFAULT_CONFIG["skip_uniqueness_checker"],
                help="Whether to skip checking for unique posts in ghost website"
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
    with start_transaction(op="task", description="Streamlit App Execution"):
        try:
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
        except Exception as e:
            logger.error(f"Error in Streamlit app: {str(e)}")
            sentry_sdk.capture_exception(e)
            st.error(f"Error: {str(e)}")
