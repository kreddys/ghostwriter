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
    
    combined_results = []
    search_errors = []
    at_least_one_successful = False

    # Google Search
    try:
        google_results = await google_search(query, config=config, state=state)
        if google_results:
            combined_results.extend(google_results)
            at_least_one_successful = True
            logger.info(f"Retrieved {len(google_results)} results from Google")
    except Exception as e:
        error_msg = f"Google search failed: {str(e)}"
        logger.error(error_msg)
        search_errors.append(error_msg)

    # Tavily Search
    try:
        tavily_results = await tavily_search(query, config=config, state=state)
        if tavily_results:
            combined_results.extend(tavily_results)
            at_least_one_successful = True
            logger.info(f"Retrieved {len(tavily_results)} results from Tavily")
    except Exception as e:
        error_msg = f"Tavily search failed: {str(e)}"
        logger.error(error_msg)
        search_errors.append(error_msg)

    # SerpAPI Search
    try:
        serp_results = await serp_search(query, config=config, state=state)
        if serp_results:
            combined_results.extend(serp_results)
            at_least_one_successful = True
            logger.info(f"Retrieved {len(serp_results)} results from SerpAPI")
    except Exception as e:
        error_msg = f"SerpAPI search failed: {str(e)}"
        logger.error(error_msg)
        search_errors.append(error_msg)

    # Check if at least one search was successful
    if not at_least_one_successful:
        error_message = "All search engines failed. Errors: " + "; ".join(search_errors)
        logger.error(error_message)
        raise ValueError(error_message)

    # Log warnings for failed searches if any
    if search_errors:
        logger.warning(f"Some searches failed but continuing with available results. Errors: {'; '.join(search_errors)}")

    logger.info(f"Combined {len(combined_results)} total results before filtering")

    try:
        # Store raw results
        state.raw_search_results[query] = combined_results
        logger.info(f"Stored {len(combined_results)} raw results")
        
        # Filter out existing URLs
        filtered_results = await filter_existing_urls(combined_results)
        logger.info(f"Filtered down to {len(filtered_results)} new results after URL filtering")

        # Store URL filtered results
        state.url_filtered_results[query] = filtered_results
        
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
        logger.error(f"Error processing search results: {str(e)}", exc_info=True)
        # If we have results but processing failed, return raw combined results
        return combined_results if combined_results else None
