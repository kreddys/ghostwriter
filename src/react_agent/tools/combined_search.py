"""Combined search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from ..utils.google_search import google_search
from ..utils.tavily_search import tavily_search
from ..utils.serp_search import serp_search
from ..utils.url_filter import filter_existing_urls
from ..state import State

logger = logging.getLogger(__name__)

async def combined_search(
    query: str, *, 
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Combine results from Google, Tavily, and SerpAPI search."""
    logger.info(f"Starting combined search for query: {query}")
    
    try:
        # Get results from all sources
        google_results = await google_search(query, config=config, state=state)
        logger.info(f"Retrieved {len(google_results) if google_results else 0} results from Google")
        
        tavily_results = await tavily_search(query, config=config, state=state)
        logger.info(f"Retrieved {len(tavily_results) if tavily_results else 0} results from Tavily")
        
        serp_results = await serp_search(query, config=config, state=state)
        logger.info(f"Retrieved {len(serp_results) if serp_results else 0} results from SerpAPI")
        
        # Combine results
        combined_results = []
        if google_results:
            combined_results.extend(google_results)
        if tavily_results:
            combined_results.extend(tavily_results)
        if serp_results:
            combined_results.extend(serp_results)
            
        logger.info(f"Combined {len(combined_results)} total results before filtering")

        # Store raw results
        state.raw_search_results[query] = combined_results
        logger.info(f"Stored {len(combined_results)} raw results")
        
        # Filter out existing URLs
        filtered_results = await filter_existing_urls(combined_results)
        logger.info(f"Filtered down to {len(filtered_results)} new results after URL filtering")

        # Store URL filtered results
        state.url_filtered_results[query] = filtered_results
        logger.info(f"Stored {len(filtered_results)} URL-filtered results")
        
        # Sort by date if available
        try:
            filtered_results.sort(
                key=lambda x: x.get('published_date', ''), 
                reverse=True
            )
        except Exception as e:
            logger.warning(f"Error sorting results by date: {str(e)}")
        
        # Update state with final results
        state.search_results[query] = filtered_results
        
        logger.info(f"Combined search completed with {len(filtered_results)} final results")
        return filtered_results
        
    except Exception as e:
        logger.error(f"Error in combined search: {str(e)}", exc_info=True)
        return None