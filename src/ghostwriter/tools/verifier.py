"""Tool for checking uniqueness of search results using LightRAG."""
import logging
from typing import Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from ..state import State
from ..configuration import Configuration
from ..utils.verify.url_filter import filter_existing_urls
from ..utils.verify.relevance_checker import RelevanceChecker

logger = logging.getLogger(__name__)


async def verifier(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> State:
    """Filter and return unique and relevant search results using LightRAG."""
    logger.info("=== Starting Uniqueness and Relevance Checker ===")
    
    # Initialize checker state
    if 'checker' not in state.tool_states:
        state.tool_states['checker'] = {
            'unique_results': {},
            'non_unique_results': {},
            'relevant_results': {},
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
        skip_uniqueness_checker = configuration.skip_uniqueness_checker
        
        # Initialize RelevanceChecker
        relevance_checker = RelevanceChecker(
            topic=configuration.topic,  # Replace with the actual topic
            threshold=configuration.relevance_similarity_threshold,  # Replace with the desired threshold
            configuration=configuration
        )
        
        unique_results = {}
        relevant_results = {}
        total_processed = 0
        total_relevant = 0
        
        logger.info(f"Processing {len(scraped_results)} queries")
        
        for query, results in scraped_results.items():
            if not isinstance(results, list):
                continue
                
            logger.info(f"\nProcessing query: {query}")
            logger.info(f"Results to process: {len(results)}")
            
            if use_url_filtering:
                filtered_results = filter_existing_urls(results)
                logger.info(f"Results after filtering: {len(filtered_results)}")
            else:
                filtered_results = results
            
            source_unique_results = []
            source_relevant_results = []
            
            # Process each result independently
            for result in filtered_results:
                
                if result.get('scrape_status') != 'success':
                    logger.info(f"✗ Skipped URL (scrape_status not success): {result['url']}")
                    continue    
                
                total_processed += 1
                
                # Check relevance first
                is_relevant = await relevance_checker.is_relevant(result['content'])
                if is_relevant:
                    total_relevant += 1
                    source_relevant_results.append(result)
                    logger.info(f"✓ Relevant URL: {result['url']}")
                    
                    if skip_uniqueness_checker:
                        source_unique_results.append(result)
                        logger.info(f"✓ Directly accepting URL as unique: {result['url']}")
                    
                    checker_state['decision_details'][result['url']] = {
                        'relevance': is_relevant,
                        'uniqueness': {'is_unique': skip_uniqueness_checker}
                    }
                else:
                    logger.info(f"✗ Rejected URL (not relevant): {result['url']}")
                    checker_state['decision_details'][result['url']] = {
                        'relevance': is_relevant,
                        'uniqueness': {'is_unique': False}
                    }
            
            if source_unique_results:
                unique_results[query] = source_unique_results
            if source_relevant_results:
                relevant_results[query] = source_relevant_results
        
        # Update checker state
        checker_state['unique_results'] = unique_results
        checker_state['relevant_results'] = relevant_results
        checker_state['check_successful'] = bool(unique_results)
        
        logger.info("\n=== Uniqueness and Relevance Checker Summary ===")
        logger.info(f"Total results processed: {total_processed}")
        logger.info(f"Relevant results found: {total_relevant}")
        logger.info(f"Final unique results: {sum(len(results) for results in unique_results.values())}")

        return state
        
    except Exception as e:
        logger.error(f"Error in uniqueness and relevance checker: {str(e)}")
        checker_state['check_successful'] = False
        raise
