"""Search processing workflow."""
import logging
import json
import re
from typing import List
from langchain_core.runnables import RunnableConfig
from ghostwriter.state import State
from ghostwriter.agents.query_generator import generate_queries
from ghostwriter.utils.search.search import combined_search
from ghostwriter.configuration import Configuration
from .scraper import update_results_with_crawler_data

logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

async def process_search(state: State, config: RunnableConfig) -> State:
    """Execute search using combined search functionality with multiple generated queries."""
    logger.info("Starting search process")

    # Get configuration properly using Configuration class
    configuration = Configuration.from_runnable_config(config)
    use_query_generator = configuration.use_query_generator
    
    # Initialize state attributes
    if not hasattr(state, 'search_results'):
        state.search_results = {}
    if not hasattr(state, 'url_filtered_results'):
        state.url_filtered_results = {}
    if not hasattr(state, 'search_successful'):
        state.search_successful = False
    if not hasattr(state, 'is_direct_url'):
        state.is_direct_url = False
    if not hasattr(state, 'direct_url'):
        state.direct_url = ""
        
    if not state.messages:
        logger.warning("No messages found in state")
        state.search_successful = False
        return state
        
    query = state.messages[0].content
    logger.info(f"Processing initial input: {query}")
    
    # Handle direct URL input
    if is_valid_url(query):
        logger.info(f"Direct URL input detected: {query}")
        state.is_direct_url = True
        state.direct_url = query
        
        # Use crawler utilities to process the URL
        configuration = Configuration.from_runnable_config(config)
        crawled_results = await update_results_with_crawler_data(
            [{"url": query}],
            configuration
        )
        
        if crawled_results and crawled_results[0].get("scrape_status") == "success":
            state.search_results[query.lower()] = crawled_results
            state.url_filtered_results[query.lower()] = crawled_results
            state.search_successful = True
            logger.info("Direct URL processing completed successfully")
        else:
            logger.error(f"Failed to scrape content from URL: {query}")
            state.search_successful = False
            logger.info("Direct URL processing failed")
        
        return state

    # Handle regular search queries
    try:
        # Generate search queries if enabled
        if use_query_generator:
            logger.info("Using query generator")
            search_queries = await generate_queries(
                query,
                config=config,
                state=state
            )
            
            clean_queries = []
            
            if isinstance(search_queries, list):
                try:
                    if all(isinstance(q, str) for q in search_queries):
                        clean_queries = search_queries
                        logger.info("Successfully parsed direct JSON queries")
                    else:
                        json_str = ' '.join(search_queries)
                        json_str = json_str.replace('```json', '').replace('```', '').strip()
                        clean_queries = json.loads(json_str)
                        logger.info("Successfully parsed markdown JSON queries")
                        
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Error parsing queries: {str(e)}. Using original query.")
                    clean_queries = [query]
                    
            else:
                logger.warning("Invalid query format. Using original query.")
                clean_queries = [query]
        else:
            logger.info("Query generator disabled, using original query")
            clean_queries = [query]
            
        # Perform search
        try:
            results = await combined_search(
                clean_queries,
                config=config, 
                state=state
            )
            
            if not results:
                logger.warning("No results found from search queries")
                state.search_successful = False
                return state
            
            state.search_results[query.lower()] = results
            state.url_filtered_results[query.lower()] = results
            state.search_successful = True
            logger.info(f"Retrieved and stored {len(results)} results from combined search")
            
        except Exception as e:
            logger.error(f"Error in combined search: {str(e)}")
            # Fallback to original query
            try:
                results = await combined_search(
                    [query],
                    config=config,
                    state=state
                )
                if results:
                    state.url_filtered_results[query.lower()] = results
                    state.search_successful = True
                else:
                    state.search_successful = False
            except Exception as e2:
                logger.error(f"Fallback search also failed: {str(e2)}")
                state.search_successful = False
            
    except Exception as e:
        logger.error(f"Error in process_search: {str(e)}")
        # Final fallback attempt
        try:
            results = await combined_search(
                [query],
                config=config,
                state=state
            )
            if results:
                state.url_filtered_results[query.lower()] = results
                state.search_successful = True
            else:
                state.search_successful = False
        except Exception as e2:
            logger.error(f"Final fallback search failed: {str(e2)}")
            state.search_successful = False
        
    return state
