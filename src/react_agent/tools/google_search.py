"""Google Search functionality."""
import os
import logging
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..configuration import Configuration
from ..state import State

logger = logging.getLogger(__name__)

async def google_search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Search the web using Google Custom Search API."""
    logger.info(f"Starting Google search for query: {query}")
    
    try:
        configuration = Configuration.from_runnable_config(config)
        
        google_api_key = os.getenv("GOOGLE_API_KEY")
        google_cse_id = os.getenv("GOOGLE_CSE_ID")        

        if not google_api_key or not google_cse_id:
            logger.error("Missing Google API credentials - API key or CSE ID not found")
            raise ValueError("Google API key or CSE ID not found in environment variables")
        
        logger.debug("Building Google Custom Search service")
        service = build("customsearch", "v1", developerKey=google_api_key)

        # Add date restriction based on configuration
        date_restrict = f"d{configuration.search_days}"

        logger.info(f"Executing Google search with max results: {configuration.max_search_results}")
        result = service.cse().list(
            q=query,
            cx=google_cse_id,
            num=configuration.max_search_results,
            dateRestrict=date_restrict,  # Add date restriction
            sort='date'  # Sort by date
        ).execute()
        
        logger.debug(f"Raw Google API response: {result}")
        processed_results = []
        
        if 'items' in result:
            logger.info(f"Found {len(result['items'])} results from Google search")
            for item in result['items']:
                processed_results.append({
                    "type": "text",
                    "title": item.get('title', 'N/A'),
                    "url": item.get('link', 'N/A'),
                    "content": item.get('snippet', 'N/A'),
                    "source": "google"
                })
        else:
            logger.warning("No items found in Google search response")
        
        state.previous_searches.add(query)
        if query not in state.search_results:
            state.search_results[query] = []
        state.search_results[query].extend(processed_results)
        
        logger.info(f"Successfully processed {len(processed_results)} Google search results")
        return processed_results
        
    except HttpError as e:
        logger.error(f"Google Search API error: {str(e)}", exc_info=True)
        raise ValueError(f"Google Search API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in Google search: {str(e)}", exc_info=True)
        raise ValueError(f"Error performing Google search: {str(e)}")