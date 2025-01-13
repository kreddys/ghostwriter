"""Combined search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List, Union
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from ..utils.google_search import google_search
from ..utils.tavily_search import tavily_search
from ..utils.serp_search import serp_search
from ..configuration import Configuration
from ..state import State

logger = logging.getLogger(__name__)

SEARCH_ENGINE_MAPPING = {
    "google": google_search,
    "tavily": tavily_search,
    "serp": serp_search
}

async def combined_search(
    queries: Union[str, List[str]],
    config: RunnableConfig,
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """
    Combined search functionality that:
    1. Executes searches for all queries using configured search engines
    2. Removes duplicate URLs
    3. Applies Supabase URL filtering
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
    
    logger.info(f"Total combined search results: {len(all_results)}")
    logger.info(f"All combined URLs: {[result.get('url') for result in all_results]}")
    
    return all_results