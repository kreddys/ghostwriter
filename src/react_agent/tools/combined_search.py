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
    queries: Union[str, List[str]], *, 
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Combine results from Google, Tavily, and SerpAPI search.
    
    Args:
        queries: Either a single query string or a list of query strings
        config: Runnable configuration
        state: Application state
        
    Returns:
        List of filtered search results or None if all searches fail
    """
    # Convert single query to list for consistent handling
    query_list = [queries] if isinstance(queries, str) else queries
    logger.info(f"Starting combined search for {len(query_list)} queries")
    
    all_combined_results = []
    
    for query in query_list:
        logger.info(f"Processing query: {query}")
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

        # Check if at least one search was successful for this query
        if not at_least_one_successful:
            error_message = f"All search engines failed for query '{query}'. Errors: " + "; ".join(search_errors)
            logger.error(error_message)
            continue  # Skip to next query instead of raising error

        # Log warnings for failed searches if any
        if search_errors:
            logger.warning(f"Some searches failed for query '{query}' but continuing with available results. Errors: {'; '.join(search_errors)}")

        logger.info(f"Combined {len(combined_results)} total results before filtering for query '{query}'")

        try:
            # Store raw results
            state.raw_search_results[query] = combined_results
            logger.info(f"Stored {len(combined_results)} raw results for query '{query}'")
            
            # Filter out existing URLs
            filtered_results = await filter_existing_urls(combined_results)
            logger.info(f"Filtered down to {len(filtered_results)} new results after URL filtering for query '{query}'")

            # Store URL filtered results
            #state.url_filtered_results[query] = filtered_results
            
            # Sort by date if available
            try:
                filtered_results.sort(
                    key=lambda x: x.get('published_date', ''), 
                    reverse=True
                )
            except Exception as e:
                logger.warning(f"Error sorting results by date for query '{query}': {str(e)}")
            
            # Update state with final results
            #state.search_results[query] = filtered_results
            
            # Add filtered results to overall results
            all_combined_results.extend(filtered_results)

        except Exception as e:
            logger.error(f"Error processing search results for query '{query}': {str(e)}", exc_info=True)
            # If we have results but processing failed, add raw results
            all_combined_results.extend(combined_results)

    # Final processing of all results
    if not all_combined_results:
        logger.error("No results found across all queries")
        return None

    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    for result in all_combined_results:
        url = result.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)

    # Sort final results by date
    try:
        unique_results.sort(
            key=lambda x: x.get('published_date', ''), 
            reverse=True
        )
    except Exception as e:
        logger.warning(f"Error sorting final combined results by date: {str(e)}")

    logger.info(f"Combined search completed with {len(unique_results)} final unique results across all queries")
    return unique_results