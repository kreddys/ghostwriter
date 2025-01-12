"""Combined search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List, Union
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from ..utils.google_search import google_search
from ..utils.tavily_search import tavily_search
from ..utils.serp_search import serp_search
from ..utils.url_filter import filter_existing_urls
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
        try:
            # Google Search
            google_results = await google_search(query, config=config, state=state)
            if google_results:
                all_results.extend(google_results)
            
            # Tavily Search
            tavily_results = await tavily_search(query, config=config, state=state)
            if tavily_results:
                all_results.extend(tavily_results)
            
            # SerpAPI Search
            serp_results = await serp_search(query, config=config, state=state)
            if serp_results:
                all_results.extend(serp_results)
                
        except Exception as e:
            logger.error(f"Error searching for query '{query}': {str(e)}")
            continue
    
    if not all_results:
        logger.warning("No results found from any search provider")
        return None
        
    # Store raw results in state
    if hasattr(state, 'raw_search_results'):
        state.raw_search_results = all_results
    
    # Step 2: Remove duplicate URLs
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get('url')
        if url and url not in seen_urls:
            unique_results.append(result)
            seen_urls.add(url)
    
    logger.info(f"Found {len(unique_results)} unique URLs from {len(all_results)} total results")
    
    # Step 3: Apply Supabase URL filtering
    try:
        filtered_results = await filter_existing_urls(unique_results)
        
        if not filtered_results:
            logger.warning("No results remained after URL filtering")
            return None
            
        logger.info(f"Found {len(filtered_results)} results after URL filtering")
        
        # Store filtered results in state - FIX: Store as dictionary with query as key
        if hasattr(state, 'url_filtered_results'):
            # Get the original query if it exists in the first query of queries list
            query_key = queries[0] if queries else "default"
            if isinstance(state.url_filtered_results, dict):
                state.url_filtered_results[query_key] = filtered_results
            else:
                # Initialize as dictionary if it's not
                state.url_filtered_results = {query_key: filtered_results}
        
        return filtered_results
        
    except Exception as e:
        logger.error(f"Error in URL filtering: {str(e)}")
        return None