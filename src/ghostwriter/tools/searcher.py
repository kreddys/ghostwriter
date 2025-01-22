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
    logger.debug(f"Initial state: {state}")

    # Get configuration properly using Configuration class
    configuration = Configuration.from_runnable_config(config)
    use_query_generator = configuration.use_query_generator
    logger.debug(f"Configuration: use_query_generator={use_query_generator}")
    
    # Initialize searcher state
    if 'searcher' not in state.tool_states:
        state.tool_states['searcher'] = {
            'search_results': {},
            'search_successful': False
        }
    searcher_state = state.tool_states['searcher']
        
    if not state.messages:
        logger.warning("No messages found in state")
        searcher_state['search_successful'] = False
        return state
        
    query = state.messages[0].content
    logger.info(f"Processing initial input: {query}")
    logger.debug(f"Full message content: {state.messages[0]}")
    
    # Handle direct URLs by formatting them as search results
    if is_valid_url(query):
        searcher_state['search_results'][f"direct:{query}"] = [{
            'url': query,
            'title': 'Direct URL',
            'content': '',
            'metadata': {},
            'search_source': 'direct_url'
        }]
        searcher_state['search_successful'] = True
        return state
        
    # Generate search queries if enabled
    clean_queries = [query]
    if use_query_generator:
        logger.info("Using query generator")
        try:
            search_queries = await generate_queries(
                query,
                config=config,
                state=state
            )
            
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
            else:
                logger.warning("Invalid query format. Using original query.")
        except Exception as e:
            logger.error(f"Error in query generation: {str(e)}")
            clean_queries = [query]  # Fallback to original query if generation fails
            
    # Perform search with consolidated error handling
    try:
        results = await combined_search(
            clean_queries,
            config=config, 
            state=state
        )
        
        if results:
            searcher_state['search_results'][f"search:{query}"] = results
            searcher_state['search_successful'] = True
            logger.info(f"Retrieved and stored {len(results)} results from search")
        else:
            logger.warning("No results found from search queries")
            searcher_state['search_successful'] = False
            
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        searcher_state['search_successful'] = False
        
    return state
