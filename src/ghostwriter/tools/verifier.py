"""Tool for checking uniqueness of search results using LightRAG."""
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
            
            # Split results into chunks
            chunks = create_chunks(filtered_results, chunk_size=5, min_content_length=100)
            logger.info(f"Created {len(chunks)} chunks for query: {query}")
            
            # Process each chunk
            for chunk in chunks:
                logger.info(f"Processing chunk with {len(chunk)} results")
                
                # Check uniqueness for the entire chunk using LightRAG
                chunk_uniqueness = await check_chunk_uniqueness(chunk, configuration)
                if not chunk_uniqueness['is_unique']:
                    logger.info(f"✗ Chunk rejected (not unique): {chunk_uniqueness['reason']}")
                    continue
                
                # If chunk is unique, add all results in the chunk to unique_results
                for result in chunk:
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
                        'reason': chunk_uniqueness.get('reason', '')
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

def create_chunks(
    results: list,
    chunk_size: int = 5,
    min_content_length: int = 100
) -> list:
    """
    Split results into chunks using a comprehensive strategy.
    
    Args:
        results: List of results to chunk.
        chunk_size: Maximum number of results per chunk.
        min_content_length: Minimum content length for a chunk to be valid.
    
    Returns:
        List of chunks, where each chunk is a list of results.
    """
    chunks = []
    current_chunk = []
    current_chunk_content_length = 0
    
    for result in results:
        content = result.get('content', '')
        content_length = len(content)
        
        # If adding this result would exceed the chunk size or content length limit,
        # finalize the current chunk and start a new one
        if (len(current_chunk) >= chunk_size or
            current_chunk_content_length + content_length > min_content_length):
            chunks.append(current_chunk)
            current_chunk = []
            current_chunk_content_length = 0
        
        current_chunk.append(result)
        current_chunk_content_length += content_length
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

async def check_chunk_uniqueness(
    chunk: list,
    configuration: Configuration
) -> dict:
    """Check if a chunk of results is unique using LightRAG."""
    try:
        # Combine chunk content into a single string for LightRAG query
        chunk_content = "\n".join([result.get('content', '') for result in chunk])
        
        # Query LightRAG to check uniqueness of the chunk
        query_data = {
            "query": f"Is the following content not covered and unique in the knowledge base? Content: {chunk_content}",
            "mode": "hybrid",
            "stream": False,
            "only_need_context": False
        }
        
        response = requests.post(
            "http://localhost:9621/query",  # Local LightRAG API endpoint
            headers={"Content-Type": "application/json"},  # Only content type header is needed
            json=query_data  # Payload for the request
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse LightRAG response
        rag_response = response.json()
        response_text = rag_response.get('response', '')
        
        # Extract JSON string from Markdown code block
        json_match = re.search(r'```json\n({.*?})\n```', response_text, re.DOTALL)
        if not json_match:
            raise ValueError("Failed to extract JSON from LightRAG response.")
        
        # Parse the extracted JSON string
        uniqueness_info = json.loads(json_match.group(1))
        
        is_unique = uniqueness_info.get('is_unique', False)
        reason = uniqueness_info.get('reason', 'No reason provided')
        
        return {
            'is_unique': is_unique,
            'reason': reason
        }
        
    except Exception as e:
        logger.error(f"Error checking chunk uniqueness: {str(e)}")
        return {
            'is_unique': False,
            'reason': f"Error: {str(e)}"
        }