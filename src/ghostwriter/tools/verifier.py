"""Tool for checking uniqueness of search results using LightRAG."""
import logging
from typing import Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from ..state import State
from ..configuration import Configuration
from ..utils.verify.url_filter_supabase import filter_existing_urls
from ..utils.verify.uniqueness_checker import check_uniqueness

logger = logging.getLogger(__name__)


async def verifier(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> State:
    """Filter and return unique search results using LightRAG."""
    logger.info("=== Starting Uniqueness Checker ===")
    
    # Initialize checker state
    if 'checker' not in state.tool_states:
        state.tool_states['checker'] = {
            'unique_results': {},
            'non_unique_results': {},
            'check_successful': False,
            'decision_details': {}
        }
    checker_state = state.tool_states['checker']
    
    try:
        # Get scraper results
        scraper_state = state.tool_states.get('scraper', {})
        if not scraper_state.get('scrape_successful', False):
            logger.warning("Scraping was not successful")
            checker_state['check_successful'] = False
            return state
            
        scraped_results = scraper_state.get('scraped_results', {})
        if not scraped_results:
            logger.warning("No scraped results found")
            checker_state['check_successful'] = False
            return state
            
        configuration = Configuration.from_runnable_config(config)
        use_url_filtering = configuration.use_url_filtering
        
        unique_results = {}
        total_processed = 0
        total_unique = 0
        
        logger.info(f"Processing {len(scraped_results)} queries")
        
        for query, results in scraped_results.items():
            if not isinstance(results, list):
                continue
                
            logger.info(f"\nProcessing query: {query}")
            logger.info(f"Results to process: {len(results)}")
            
            if use_url_filtering:
                filtered_results = await filter_existing_urls(results)
                logger.info(f"Results after filtering: {len(filtered_results)}")
            else:
                filtered_results = results
            
            source_unique_results = []
            
            # Process each result independently
            for result in filtered_results:
                total_processed += 1
                
                # Check uniqueness for individual result
                uniqueness_check = await check_uniqueness(result, configuration)
                
                if uniqueness_check['is_unique']:
                    total_unique += 1
                    source_unique_results.append(result)
                    logger.info(f"✓ Accepted URL (unique): {uniqueness_check['url']}")
                else:
                    logger.info(f"✗ Rejected URL (not unique): {uniqueness_check['url']}")
                
                # Store decision details
                checker_state['decision_details'][uniqueness_check['url']] = uniqueness_check
            
            if source_unique_results:
                unique_results[query] = source_unique_results
        
        # Update checker state
        checker_state['unique_results'] = unique_results
        if unique_results:
            checker_state['check_successful'] = True
        else:
            checker_state['check_successful'] = False
        
        logger.info("\n=== Uniqueness Checker Summary ===")
        logger.info(f"Total results processed: {total_processed}")
        logger.info(f"Unique results found: {total_unique}")
        logger.info(f"Final unique results: {sum(len(results) for results in unique_results.values())}")

        return state
        
    except Exception as e:
        logger.error(f"Error in uniqueness checker: {str(e)}")
        checker_state['check_successful'] = False
        raise
