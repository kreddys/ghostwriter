"""Tool for checking uniqueness of search results using LightRAG."""
import logging
from typing import Dict, Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_core.messages import SystemMessage
from ..state import State
from ..configuration import Configuration
from ..prompts import RELEVANCY_CHECK_PROMPT 
from ..llm import get_llm
from ..utils.unique.url_filter_supabase import filter_existing_urls
from ..utils.unique.checker_utils import (
    init_lightrag_with_ghost_articles,
    check_result_uniqueness
)

logger = logging.getLogger(__name__)

async def check_content_relevancy(content: dict, topic: str, model) -> dict:
    """Check if content is relevant to the specified topic using LLM."""
    url = content.get('url', 'No URL')
    title = content.get('title', 'No title')
    
    logger.info(f"Checking relevancy for URL: {url}")
    logger.info(f"Title: {title}")
    logger.info(f"Topic: {topic}")
    
    try:
        messages = [
            SystemMessage(
                content=RELEVANCY_CHECK_PROMPT.format(
                    topic=topic,
                    title=title,
                    content=content.get('content', 'N/A')
                )
            )
        ]
        
        response = await model.ainvoke(messages)
        response_text = response.content.lower()
        is_relevant = response_text.startswith('relevant')
        reason = response_text.split(':', 1)[1].strip() if ':' in response_text else ''
        
        logger.info(f"Relevancy check result for {url}: {'RELEVANT' if is_relevant else 'NOT RELEVANT'} - {reason}")
        return {
            'is_relevant': is_relevant,
            'reason': reason
        }
        
    except Exception as e:
        logger.error(f"Error in relevancy check for {url}: {str(e)}")
        return {
            'is_relevant': False,
            'reason': f"Error: {str(e)}"
        }

async def uniqueness_checker(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> State:
    """Filter and return unique search results using LightRAG and check topic relevancy."""
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
        # Check if we have direct_url results from searcher
        searcher_state = state.tool_states.get('searcher', {})
        search_results = searcher_state.get('search_results', {})
        
        # Check for direct_url results
        direct_results = {}
        for query, results in search_results.items():
            if results and isinstance(results, list) and len(results) > 0:
                if results[0].get('search_source') == 'direct_url':
                    direct_results[query] = results
                    logger.info(f"Found direct URL results for query: {query}")
        
        if direct_results:
            # Skip verification for direct URLs but ensure content is passed through
            logger.info("Processing direct URLs - skipping verification")
            for query, results in direct_results.items():
                # Get the corresponding scraped content
                scraper_state = state.tool_states.get('scraper', {})
                scraped_results = scraper_state.get('scraped_results', {})
                if query in scraped_results:
                    # Update results with scraped content
                    scraped_content = scraped_results[query][0].get('content', '')
                    results[0]['content'] = scraped_content
                    logger.info(f"Added scraped content to direct URL result: {query}")
            
            checker_state['unique_results'] = direct_results
            checker_state['check_successful'] = True
            return state
            
        # Proceed with normal verification for non-direct URLs
        logger.info("Fetching scraper results...")
        scraper_state = state.tool_states.get('scraper', {})
        scraped_results = scraper_state.get('scraped_results', {})
        
        if not scraped_results:
            logger.warning("=== No Scraped Results Found ===")
            logger.warning("Skipping uniqueness check - no results to process")
            checker_state['check_successful'] = False
            return state
            
        configuration = Configuration.from_runnable_config(config)
        use_url_filtering = configuration.use_url_filtering
        model = get_llm(configuration, temperature=0.3)
        
        logger.info("Initializing LightRAG knowledge store...")
        rag = await init_lightrag_with_ghost_articles()
        
        unique_results = {}
        total_processed = 0
        total_unique = 0
        total_relevant = 0
        
        logger.info(f"\n=== Processing {len(scraped_results)} Queries ===")
        for query, results in scraped_results.items():
            if not isinstance(results, list):
                continue
                
            logger.info(f"\n=== Processing Query ===")
            logger.info(f"Query: {query}")
            logger.info(f"Results to process: {len(results)}")
            
            if use_url_filtering:
                logger.info("Applying URL filtering...")
                filtered_results = await filter_existing_urls(results)
                logger.info(f"Results after filtering: {len(filtered_results)}")
                logger.info(f"Results filtered out: {len(results) - len(filtered_results)}")
            else:
                logger.info("URL filtering disabled - processing all results")
                filtered_results = results
            
            source_unique_results = []
            
            logger.info(f"Processing {len(filtered_results)} results...")
            for result in filtered_results:
                total_processed += 1
                url = result.get('url', 'No URL')
                
                logger.info(f"\nProcessing result {total_processed}: {url}")
                
                # Check uniqueness with detailed results
                uniqueness_result = check_result_uniqueness(result, rag, configuration)
                is_unique = uniqueness_result['is_unique']
                similarity_score = uniqueness_result.get('similarity_score', 0)
                similar_url = uniqueness_result.get('similar_url', '')
                
                decision_details = {
                    'url': result.get('url'),
                    'title': result.get('title'),
                    'similarity_score': similarity_score,
                    'similar_url': similar_url,
                    'threshold': configuration.similarity_threshold
                }
                
                if is_unique:
                    total_unique += 1
                    logger.info(f"Result is unique (score: {similarity_score}) - checking relevancy...")
                    
                    # Check relevancy with detailed results
                    relevancy_result = await check_content_relevancy(result, configuration.topic, model)
                    is_relevant = relevancy_result['is_relevant']
                    relevancy_reason = relevancy_result.get('reason', '')
                    
                    decision_details.update({
                        'is_relevant': is_relevant,
                        'relevancy_reason': relevancy_reason
                    })
                    
                    if is_relevant:
                        total_relevant += 1
                        source_unique_results.append(result)
                        logger.info("✓ Result accepted (unique and relevant)")
                    else:
                        logger.info(f"✗ Result rejected (not relevant): {relevancy_reason}")
                        checker_state['non_unique_results'].setdefault(query, []).append({
                            'result': result,
                            'reason': f"Not relevant: {relevancy_reason}",
                            'details': decision_details
                        })
                else:
                    logger.info(f"✗ Result rejected (not unique). Similar to: {similar_url} (score: {similarity_score})")
                    checker_state['non_unique_results'].setdefault(query, []).append({
                        'result': result,
                        'reason': f"Not unique. Similar to: {similar_url} (score: {similarity_score})",
                        'details': decision_details
                    })
                
                # Store decision details
                checker_state['decision_details'][result.get('url')] = decision_details
            
            if source_unique_results:
                unique_results[query] = source_unique_results
                logger.info(f"Stored {len(source_unique_results)} unique results for query")
        
        # Update checker state
        checker_state['unique_results'] = unique_results
        checker_state['check_successful'] = True
        
        logger.info("\n=== Uniqueness Checker Summary ===")
        logger.info(f"Total results processed: {total_processed}")
        logger.info(f"Unique results found: {total_unique}")
        logger.info(f"Relevant results found: {total_relevant}")
        logger.info(f"Final unique and relevant results: {sum(len(results) for results in unique_results.values())}")
        logger.info("=== Uniqueness Checker Completed ===")

        return state
        
    except Exception as e:
        logger.error(f"Error in uniqueness checker: {str(e)}")
        checker_state['check_successful'] = False
        raise
