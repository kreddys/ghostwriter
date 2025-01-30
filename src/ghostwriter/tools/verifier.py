"""Tool for checking uniqueness of search results using LightRAG."""
import os
import logging
import requests
import json
import re
from typing import Dict, Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from ..state import State
from ..configuration import Configuration
from ..utils.unique.url_filter_supabase import filter_existing_urls
from ..prompts import CONTENT_VERIFICATION_PROMPT
from ..utils.unique.checker_utils import split_content_into_chunks, truncate_content

logger = logging.getLogger(__name__)

async def check_uniqueness(
    result: Dict,
    configuration: Configuration
) -> dict:
    """Check if an individual result is unique using LightRAG.
    
    Args:
        result: Single content result to check for uniqueness
        configuration: Configuration object containing settings
        
    Returns:
        dict: Contains uniqueness check results
    """
    try:
        # Get endpoint and API key
        lightrag_endpoint = os.getenv("LIGHTRAG_ENDPOINT")
        lightrag_apikey = os.getenv("LIGHTRAG_APIKEY")

        if not lightrag_endpoint or not lightrag_apikey:
            logger.error("Missing LightRAG credentials")
            raise ValueError("LIGHTRAG_ENDPOINT or LIGHTRAG_APIKEY not set")

        url = result.get('url', 'No URL')
        title = result.get('title', 'No title')
        content = result.get('content', '')

        if not content.strip():
            logger.error(f"No content found for URL: {url}")
            return {
                'is_unique': False,
                'reason': "No content to check",
                'url': url,
                'title': title
            }

        # Truncate content if too long
        content = truncate_content(content)
        
        # Split into chunks
        chunks = split_content_into_chunks(
            content,
            chunk_size=configuration.chunk_size or 500,
            chunk_overlap=configuration.chunk_overlap or 50
        )

        logger.info(f"Processing {len(chunks)} chunks for URL: {url}")

        for i, chunk in enumerate(chunks, 1):
            try:
                # Prepare query data for this chunk
                query_data = {
                    "query": CONTENT_VERIFICATION_PROMPT.format(combined_content=chunk),
                    "mode": "hybrid",
                    "stream": False,
                    "only_need_context": False,
                }

                # Make API request
                response = requests.post(
                    lightrag_endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": lightrag_apikey,
                    },
                    json=query_data,
                    timeout=configuration.lightrag_timeout
                )
                
                logger.info(f"Chunk {i} response status: {response.status_code}")
                response.raise_for_status()
                
                rag_response = response.json()
                
                # Extract JSON from response
                json_match = re.search(r'```json\n({.*?})\n```', rag_response.get('response', ''), re.DOTALL)
                if not json_match:
                    logger.warning(f"Failed to extract JSON from chunk {i} response")
                    continue

                uniqueness_info = json.loads(json_match.group(1))
                
                # If any chunk is unique, consider the content unique
                if not uniqueness_info.get('is_present', True):
                    return {
                        'is_unique': True,
                        'reason': f"Unique content found in chunk {i}: {uniqueness_info.get('reason', '')}",
                        'url': url,
                        'title': title
                    }

            except Exception as e:
                logger.error(f"Error processing chunk {i} for {url}: {str(e)}")
                continue

        # If no chunks were unique
        return {
            'is_unique': False,
            'reason': "Content similar to existing articles",
            'url': url,
            'title': title
        }

    except Exception as e:
        logger.error(f"Error checking uniqueness: {str(e)}")
        return {
            'is_unique': False,
            'reason': f"Error: {str(e)}",
            'url': url,
            'title': title
        }

async def uniqueness_checker(
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
        checker_state['check_successful'] = True
        
        logger.info("\n=== Uniqueness Checker Summary ===")
        logger.info(f"Total results processed: {total_processed}")
        logger.info(f"Unique results found: {total_unique}")
        logger.info(f"Final unique results: {sum(len(results) for results in unique_results.values())}")

        return state
        
    except Exception as e:
        logger.error(f"Error in uniqueness checker: {str(e)}")
        checker_state['check_successful'] = False
        raise