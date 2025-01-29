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

logger = logging.getLogger(__name__)

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
        # Check if we have direct_url results from searcher
        searcher_state = state.tool_states.get('searcher', {})
        search_results = searcher_state.get('search_results', {})
        
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
        
        unique_results = {}
        total_processed = 0
        total_unique = 0
        
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
            
            # Check uniqueness for the entire set of results using LightRAG
            uniqueness_check = await check_uniqueness(filtered_results, configuration)
            if not uniqueness_check['is_unique']:
                logger.info(f"✗ Results rejected (not unique): {uniqueness_check['reason']}")
                continue
            
            # If results are unique, add all results to unique_results
            for result in filtered_results:
                total_processed += 1
                url = result.get('url', 'No URL')
                logger.info(f"✓ Accepted: {url} (unique)")
                source_unique_results.append(result)
                total_unique += 1
                
                # Store decision details
                checker_state['decision_details'][url] = {
                    'url': url,
                    'title': result.get('title', 'No title'),
                    'is_unique': True,
                    'reason': uniqueness_check.get('reason', '')
                }
            
            if source_unique_results:
                unique_results[query] = source_unique_results
        
        # Update checker state
        checker_state['unique_results'] = unique_results
        checker_state['check_successful'] = True
        
        logger.info("\n=== Uniqueness Checker Summary ===")
        logger.info(f"Total results processed: {total_processed}")
        logger.info(f"Unique results found: {total_unique}")
        logger.info(f"Final unique results: {sum(len(results) for results in unique_results.values())}")
        logger.info("=== Uniqueness Checker Completed ===")

        return state
        
    except Exception as e:
        logger.error(f"Error in uniqueness checker: {str(e)}")
        checker_state['check_successful'] = False
        raise

async def check_uniqueness(
    results: list,
    configuration: Configuration
) -> dict:
    """Check if a set of results is unique using LightRAG."""
    try:
        # Get endpoint and API key from environment variables
        lightrag_endpoint = os.getenv("LIGHTRAG_ENDPOINT")
        lightrag_apikey = os.getenv("LIGHTRAG_APIKEY")

        if not lightrag_endpoint or not lightrag_apikey:
            raise ValueError("LIGHTRAG_ENDPOINT or LIGHTRAG_APIKEY is not set in the .env file.")

        # Combine results content into a single string for LightRAG query
        combined_content = "\n".join([result.get('content', '') for result in results])
        
        # Query LightRAG to check uniqueness of the combined content
        query_data = {
            "query": f"Check if the following content is already present in the knowledge base. Must always Return a JSON response with 'is_present' (boolean) and 'reason' (string) fields. Content: {combined_content}",
            "mode": "hybrid",
            "stream": False,
            "only_need_context": False,
        }
        
        response = requests.post(
            lightrag_endpoint,  # Use endpoint from environment variable
            headers={
                "Content-Type": "application/json",
                "X-API-Key": lightrag_apikey,  # Use API key from environment variable
            },
            json=query_data  # Payload for the request
        )
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Log the raw response content for debugging
        raw_response = response.text
        logger.info(f"Raw API response: {raw_response}")
        
        # Parse the API response
        rag_response = response.json()
        
        # Extract the JSON string from the Markdown code block
        json_match = re.search(r'```json\n({.*?})\n```', rag_response['response'], re.DOTALL)
        if not json_match:
            raise ValueError("Failed to extract JSON from LightRAG response.")
        
        # Parse the extracted JSON string
        uniqueness_info = json.loads(json_match.group(1))
        
        # Ensure the response has the expected fields
        if not all(key in uniqueness_info for key in ['is_present', 'reason']):
            raise ValueError("API response is missing required fields: 'is_present' or 'reason'.")
        
        is_present = uniqueness_info['is_present']
        reason = uniqueness_info['reason']
        
        return {
            'is_unique': not is_present,  # Invert is_present to get is_unique
            'reason': reason
        }
        
    except Exception as e:
        logger.error(f"Error checking uniqueness: {str(e)}")
        return {
            'is_unique': False,  # Assume content is not unique if there's an error
            'reason': f"Error: {str(e)}"
        }