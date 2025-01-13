"""Combined search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List, Union
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from ..utils.google_search import google_search
from ..utils.tavily_search import tavily_search
from ..utils.serp_search import serp_search
from ..state import State

logger = logging.getLogger(__name__)

async def combined_search(
    queries: Union[str, List[str]],
    config: RunnableConfig,
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """
    Combined search functionality that:
    1. Executes searches for all queries
    2. Removes duplicate URLs
    3. Applies Supabase URL filtering
    """
    logger.info("Starting combined search")
    
    # Ensure queries is a list
    if isinstance(queries, str):
        queries = [queries]
    
    all_results = []
    
    # Step 1: Execute searches for all queries and collect results
    for query in queries:
        # Try Google Search
        try:
            google_results = await google_search(query, config=config, state=state)
            if google_results:
                all_results.extend(google_results)
        except Exception as e:
            logger.error(f"Google search failed for query '{query}': {str(e)}")
            
        # Try Tavily Search
        try:
            tavily_results = await tavily_search(query, config=config, state=state)
            if tavily_results:
                all_results.extend(tavily_results)
        except Exception as e:
            logger.error(f"Tavily search failed for query '{query}': {str(e)}")
            
        # Try SerpAPI Search
        try:
            serp_results = await serp_search(query, config=config, state=state)
            if serp_results:
                all_results.extend(serp_results)
        except Exception as e:
            logger.error(f"SerpAPI search failed for query '{query}': {str(e)}")
    
    if not all_results:
        logger.warning("No results found from any search provider")
        return None
    
    # Step 2: Remove duplicate URLs
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get('url')
        if url and url not in seen_urls:
            unique_results.append(result)
            seen_urls.add(url)
    
    logger.info(f"Found {len(unique_results)} unique URLs from {len(all_results)} total results")
    logger.info(f"All combined URLs: {[result.get('url') for result in all_results]}")
    
    return unique_results