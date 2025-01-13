"""Search processing workflow."""
import logging
import json
import re
from typing import List
from langchain_core.runnables import RunnableConfig
from react_agent.state import State
from react_agent.agents.query_generator_agent import generate_queries
from react_agent.tools.combined_search import combined_search
from react_agent.utils.url_filter import filter_existing_urls
from react_agent.configuration import Configuration

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
    use_url_filtering = configuration.use_url_filtering
    
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
    
    # Check if input is a URL
    if is_valid_url(query):
        logger.info(f"Direct URL input detected: {query}")
        state.is_direct_url = True
        state.direct_url = query
        
        # Create a direct URL result
        direct_result = {
            "url": query,
            "title": "Direct URL Input",
            "content": "Content from direct URL input",
            "source": "direct_input"
        }
        
        # Store the result in state
        state.search_results[query.lower()] = [direct_result]
        state.url_filtered_results[query.lower()] = [direct_result]
        state.search_successful = True
        
        logger.info("Direct URL processing completed")
        return state
    
    try:
        if use_query_generator and not state.is_direct_url:
            logger.info("Using query generator")
            # Generate multiple search queries using the function
            search_queries = await generate_queries(
                query,
                config=config,
                state=state
            )
            
            # Initialize clean_queries
            clean_queries = []
            
            # Handle different response formats
            if isinstance(search_queries, list):
                try:
                    # Case 1: Direct JSON list
                    if all(isinstance(q, str) for q in search_queries):
                        clean_queries = search_queries
                        logger.info("Successfully parsed direct JSON queries")
                    # Case 2: Markdown-formatted JSON
                    else:
                        json_str = ' '.join(search_queries)
                        json_str = json_str.replace('```json', '').replace('```', '').strip()
                        clean_queries = json.loads(json_str)
                        logger.info("Successfully parsed markdown JSON queries")
                        
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Error parsing queries: {str(e)}. Using original query.")
                    clean_queries = [query]  # Fallback to original query
                    
            else:
                logger.warning("Invalid query format. Using original query.")
                clean_queries = [query]  # Fallback to original query
        else:
            logger.info("Query generator disabled or direct URL mode, using original query")
            clean_queries = [query]
            
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
            logger.info(f"Retrieved {len(results)} results from combined search")
            
            if use_url_filtering and not state.is_direct_url:
                logger.info("Applying URL filtering")
                filtered_results = await filter_existing_urls(
                    search_results=state.search_results[query.lower()],
                )
                if not filtered_results:
                    logger.warning("No results after URL filtering")
                    state.search_successful = False
                    return state
                state.url_filtered_results[query.lower()] = filtered_results
                state.search_successful = True
                logger.info(f"Stored {len(filtered_results)} filtered results")
            else:
                logger.info("URL filtering disabled or direct URL mode, storing unfiltered results")
                state.url_filtered_results[query.lower()] = results
                state.search_successful = True
                logger.info(f"Stored {len(results)} unfiltered results")
            
        except Exception as e:
            logger.error(f"Error in combined search: {str(e)}")
            # Try one more time with original query if combined search fails
            try:
                results = await combined_search(
                    [query],
                    config=config,
                    state=state
                )
                if results:
                    if use_url_filtering and not state.is_direct_url:
                        filtered_results = await filter_existing_urls(
                            search_results=state.search_results[query.lower()],
                        )
                        if filtered_results:
                            state.url_filtered_results[query.lower()] = filtered_results
                            state.search_successful = True
                        else:
                            state.search_successful = False
                    else:
                        state.url_filtered_results[query.lower()] = results
                        state.search_successful = True
                else:
                    state.search_successful = False
            except Exception as e2:
                logger.error(f"Fallback search also failed: {str(e2)}")
                state.search_successful = False
            return state
            
    except Exception as e:
        logger.error(f"Error in process_search: {str(e)}")
        # Try with original query as last resort
        try:
            results = await combined_search(
                [query],
                config=config,
                state=state
            )
            if results:
                if use_url_filtering and not state.is_direct_url:
                    filtered_results = await filter_existing_urls(
                        search_results=state.search_results[query.lower()],
                    )
                    if filtered_results:
                        state.url_filtered_results[query.lower()] = filtered_results
                        state.search_successful = True
                    else:
                        state.search_successful = False
                else:
                    state.url_filtered_results[query.lower()] = results
                    state.search_successful = True
            else:
                state.search_successful = False
        except Exception as e2:
            logger.error(f"Final fallback search failed: {str(e2)}")
            state.search_successful = False
        
    return state