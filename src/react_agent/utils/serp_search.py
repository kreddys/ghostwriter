"""SerpAPI Search functionality."""
import logging
import os
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from serpapi import GoogleSearch

from ..configuration import Configuration
from ..state import State

logger = logging.getLogger(__name__)

async def serp_search(
    query: str, *, 
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Search the web using SerpAPI."""
    logger.info(f"Starting SerpAPI search for query: {query}")
    
    try:
        configuration = Configuration.from_runnable_config(config)
        
        serp_api_key = os.getenv("SERPAPI_API_KEY")
        
        if not serp_api_key:
            logger.error("Missing SerpAPI API key")
            raise ValueError("SerpAPI API key not found in environment variables")

        search_query = query
        # Add site restrictions if sites_list is configured
        if hasattr(configuration, 'sites_list') and configuration.sites_list:
            site_filter = " OR ".join(f"site:{site}" for site in configuration.sites_list)
            search_query = f"({query}) ({site_filter})"

        search_params = {
            "q": search_query,
            "api_key": serp_api_key,
            "engine": "google",
            "num": configuration.max_search_results,
            "tbs": f"qdr:d{configuration.search_days}"  # Time restriction
        }
        
        logger.info(f"Executing SerpAPI search with params: {search_params}")
        
        search = GoogleSearch(search_params)
        results = search.get_dict()
        
        logger.debug(f"Raw SerpAPI response: {results}")
        processed_results = []
        
        if "organic_results" in results:
            logger.info(f"Found {len(results['organic_results'])} results from SerpAPI search")
            for item in results["organic_results"]:
                processed_results.append({
                    "type": "text",
                    "title": item.get("title", "N/A"),
                    "url": item.get("link", "N/A"),
                    "content": item.get("snippet", "N/A"),
                    "source": "serpapi"
                })
        else:
            logger.warning("No organic results found in SerpAPI response")
        
        state.search_results[query] = processed_results
        
        logger.info(f"Successfully processed {len(processed_results)} SerpAPI search results")
        return processed_results
        
    except Exception as e:
        logger.error(f"Error in SerpAPI search: {str(e)}", exc_info=True)
        raise ValueError(f"Error performing SerpAPI search: {str(e)}")