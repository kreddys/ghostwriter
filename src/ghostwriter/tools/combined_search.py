"""Combined search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List, Union
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from ..utils.google_search import google_search
from ..utils.tavily_search import tavily_search
from ..utils.serp_search import serp_search
from ..utils.firecrawl_client import scrape_url_content
from ..configuration import Configuration
from ..state import State

logger = logging.getLogger(__name__)

SEARCH_ENGINE_MAPPING = {
    "google": google_search,
    "tavily": tavily_search,
    "serp": serp_search
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

async def update_with_firecrawl(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Update search results with Firecrawl data."""
    updated_results = []
    
    for result in results:
        url = result.get('url')
        if not url:
            result['scrape_status'] = 'failure'
            updated_results.append(result)
            continue
            
        try:
            firecrawl_data = await scrape_url_content(url)
            if firecrawl_data:
                # Merge the Firecrawl data with the original result
                merged_result = {
                    **result,
                    'title': firecrawl_data.get('title', result.get('title')),
                    'content': firecrawl_data.get('content', result.get('content')),
                    'metadata': {
                        **(result.get('metadata', {})),
                        **(firecrawl_data.get('metadata', {}))
                    },
                    'scrape_status': 'success'
                }
                logger.info(f"Successfully updated result with Firecrawl data for URL: {url}")
                updated_results.append(merged_result)
            else:
                result['scrape_status'] = 'failure'
                logger.warning(f"Firecrawl failed for URL: {url}, keeping original data")
                updated_results.append(result)
        except Exception as e:
            result['scrape_status'] = 'failure'
            logger.error(f"Error updating result with Firecrawl for URL {url}: {str(e)}")
            updated_results.append(result)
            
    return updated_results

async def combined_search(
    queries: Union[str, List[str]],
    config: RunnableConfig,
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """
    Combined search functionality that:
    1. Executes searches for all queries using configured search engines
    2. Removes duplicate URLs
    3. Updates unique results with Firecrawl data
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
                    logger.info(f"{engine_name} URLs: {[result.get('url') for result in results]}")
                    all_results.extend(results)
            except Exception as e:
                logger.error(f"{engine_name} search failed for query '{query}': {str(e)}")
    
    if not all_results:
        logger.warning("No results found from any search engine")
        return None
        
    # Step 2: Get unique results
    unique_results = get_unique_results(all_results)
    logger.info(f"Found {len(unique_results)} unique results from {len(all_results)} total results")
    
    # Step 3: Update unique results with Firecrawl
    try:
        final_results = await update_with_firecrawl(unique_results)
        logger.info(f"Successfully updated {len(final_results)} results with Firecrawl")
        return final_results
    except Exception as e:
        for result in unique_results:
            result['scrape_status'] = 'failure'
        logger.error(f"Error during Firecrawl update: {str(e)}")
        return unique_results  # Return unique results without Firecrawl updates if it fails