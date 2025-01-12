"""Search processing workflow."""
import logging
import json
from typing import List
from langchain_core.runnables import RunnableConfig
from react_agent.state import State
from react_agent.agents.query_generator_agent import generate_queries
from react_agent.tools.combined_search import combined_search

logger = logging.getLogger(__name__)

async def process_search(state: State, config: RunnableConfig) -> State:
    """Execute search using combined search functionality with multiple generated queries."""
    logger.info("Starting search process")
    
    if not hasattr(state, 'search_results'):
        state.search_results = {}
        
    if not hasattr(state, 'url_filtered_results'):
        state.url_filtered_results = {}
        
    if not state.messages:
        logger.warning("No messages found in state")
        return state
        
    query = state.messages[0].content
    logger.info(f"Processing initial query: {query}")
    
    try:
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
                    import json
                    clean_queries = json.loads(json_str)
                    logger.info("Successfully parsed markdown JSON queries")
                    
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Error parsing queries: {str(e)}. Using original query.")
                clean_queries = [query]  # Fallback to original query
                
        else:
            logger.warning("Invalid query format. Using original query.")
            clean_queries = [query]  # Fallback to original query
            
        try:
            results = await combined_search(
                clean_queries,
                config=config, 
                state=state
            )
            if not results:
                logger.warning("No results found from search queries")
                return state
                    
            logger.info(f"Retrieved {len(results)} results from combined search")
            
            # Store results in state - THIS WAS MISSING
            state.url_filtered_results[query.lower()] = results
            
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
                    state.url_filtered_results[query.lower()] = results
            except Exception as e2:
                logger.error(f"Fallback search also failed: {str(e2)}")
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
                state.url_filtered_results[query.lower()] = results
        except Exception as e2:
            logger.error(f"Final fallback search failed: {str(e2)}")
        
    return state