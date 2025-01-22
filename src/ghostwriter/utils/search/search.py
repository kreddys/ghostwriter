"""Combined search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List, Union
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from .google import google_search
from .tavily import tavily_search
from .serp import serp_search
from .youtube import youtube_search
from ...configuration import Configuration
from ...state import State

logger = logging.getLogger(__name__)

SEARCH_ENGINE_MAPPING = {
    "google": google_search,
    "tavily": tavily_search,
    "serp": serp_search,
    "youtube": youtube_search
}

def get_unique_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get unique results based on URL."""
    seen_urls = set()
    unique_results = []
    
    for result in results:
        url = result.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
            
    return unique_results

async def combined_search(
    queries: Union[str, List[str]],
    config: RunnableConfig,
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """
    Combined search functionality that:
    1. Executes searches for all queries using configured search engines
    2. Removes duplicate URLs
    3. Updates unique results with crawler data
    """
    logger.info("Starting combined search")
    
    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    
    # Determine which search engines to use
    active_engines = configuration.search_engines
    if not active_engines:  # If empty, use all available engines
        active_engines = list(SEARCH_ENGINE_MAPPING.keys())
    
    logger.info(f"Using search engines: {active_engines}")
    
    # Ensure queries is a list
    if isinstance(queries, str):
        queries = [queries]
    
    all_results = []
    
    # Step 1: Execute searches for all queries and collect results
    for query in queries:
        for engine_name in active_engines:
            search_func = SEARCH_ENGINE_MAPPING.get(engine_name)
            if not search_func:
                logger.warning(f"Unknown search engine: {engine_name}")
                continue
                
            try:
                logger.info(f"Executing {engine_name} search for query: {query}")
                results = await search_func(query, config=config, state=state)
                if results:
                    logger.info(f"{engine_name} search returned {len(results)} results")
                    all_results.extend(results)
            except Exception as e:
                logger.error(f"{engine_name} search failed for query '{query}': {str(e)}")
    
    if not all_results:
        logger.warning("No results found from any search engine")
        return None
        
    # Step 2: Get unique results
    unique_results = get_unique_results(all_results)
    logger.info(f"Found {len(unique_results)} unique results from {len(all_results)} total results")
    
    logger.info(f"Returning {len(unique_results)} unique search results")
    return unique_results
