"""Utilities for scraping content using multiple configured scrapers."""

import logging
from typing import Dict, List, Optional
from langchain_core.runnables import RunnableConfig
from ..configuration import Configuration
from ..state import State
from ..utils.scrape.firecrawl import firecrawl_scrape_url
from ..utils.scrape.youtube import scrape_youtube_video

logger = logging.getLogger(__name__)

# Define scraper mapping here
SCRAPER_MAPPING = {
    "firecrawl": firecrawl_scrape_url,
    "youtube": scrape_youtube_video
}

async def scrape_with_fallback(
    url: str, 
    config: Configuration,
    scraper_mapping: Dict = SCRAPER_MAPPING
) -> Optional[Dict]:
    """
    Attempt to scrape a URL using configured scrapers.
    For YouTube URLs, uses only YouTube scraper.
    For non-YouTube URLs, tries all active scrapers except YouTube.
    
    Args:
        url: The URL to scrape
        config: Configuration object
        scraper_mapping: Dictionary mapping scraper names to their functions
        
    Returns:
        Dictionary containing scraped content or None if all scrapers failed
    """
    from ..utils.scrape.youtube import is_youtube_url
    
    logger.info(f"Attempting to scrape URL: {url}")
    
    try:
        # Get active scrapers from config or use all available
        active_scrapers = config.scraping_engines
        if not active_scrapers:
            active_scrapers = list(scraper_mapping.keys())

        # Check if it's a YouTube URL
        if is_youtube_url(url):
            logger.info(f"Detected YouTube URL: {url}")
            youtube_scraper = scraper_mapping.get("youtube")
            if youtube_scraper:
                result = await youtube_scraper(url)
                if result:
                    return {
                        **result,
                        "scraper_used": "youtube",
                        "scrape_status": "success"
                    }
                logger.warning(f"YouTube scraper failed for URL: {url}")
        else:
            # For non-YouTube URLs, try all active scrapers except YouTube
            logger.info(f"Non-YouTube URL detected, trying other scrapers")
            for scraper_name in active_scrapers:
                # Skip YouTube scraper for non-YouTube URLs
                if scraper_name == "youtube":
                    continue
                    
                scraper_func = scraper_mapping.get(scraper_name)
                if not scraper_func:
                    logger.warning(f"Unknown scraper: {scraper_name}")
                    continue
                    
                try:
                    logger.info(f"Trying {scraper_name} for URL: {url}")
                    result = await scraper_func(url)
                    if result:
                        logger.info(f"Successfully scraped with {scraper_name}")
                        return {
                            **result,
                            "scraper_used": scraper_name,
                            "scrape_status": "success"
                        }
                    logger.warning(f"{scraper_name} failed for URL: {url}")
                except Exception as e:
                    logger.error(f"Error with {scraper_name} for URL {url}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {str(e)}")
    
    # Return failure status if all attempts fail
    return {
        "url": url,
        "scrape_status": "failure"
    }

async def scrape_multiple_urls(
    urls: List[str],
    config: Configuration,
    scraper_mapping: Dict = SCRAPER_MAPPING
) -> List[Dict]:
    """
    Scrape multiple URLs using configured scrapers with fallback logic.
    
    Args:
        urls: List of URLs to scrape
        config: Configuration object
        scraper_mapping: Dictionary mapping scraper names to their functions
        
    Returns:
        List of scraped results (successful and failed)
    """
    results = []
    
    for url in urls:
        result = await scrape_with_fallback(url, config, scraper_mapping)
        results.append(result)
            
    return results

async def process_scrape(state: State, config: RunnableConfig) -> State:
    """
    Process URLs from search results and update with crawled content.
    
    Args:
        state: Current workflow state containing search_results
        config: Runnable configuration
        
    Returns:
        Updated state with scraped content
    """
    logger.info("Starting scrape process")
    
    # Initialize scraper state
    if 'scraper' not in state.tool_states:
        state.tool_states['scraper'] = {
            'scraped_results': {},
            'scrape_successful': False
        }
    scraper_state = state.tool_states['scraper']
    
    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    
    # Get search results from searcher state
    searcher_state = state.tool_states.get('searcher', {})
    search_results = searcher_state.get('search_results', {})
    
    # Process each search result
    for query_key, results in search_results.items():
        if not results:
            continue
            
        # Get URLs to crawl
        urls = [result.get('url') for result in results if result.get('url')]
        
        # Scrape URLs using the utility
        scraped_data = await scrape_multiple_urls(urls, configuration)
        
        # Create URL to scraped data mapping
        scraped_data_map = {data['url']: data for data in scraped_data if data}
        
        # Update results with scraped content
        scraped_results = []
        for result in results:
            url = result.get('url')
            if not url:
                result['scrape_status'] = 'failure'
                scraped_results.append(result)
                continue
                
            scrape_result = scraped_data_map.get(url)
            if scrape_result and scrape_result.get('scrape_status') == 'success':
                scraped_results.append({
                    **result,
                    'title': scrape_result.get('title', result.get('title')),
                    'content': scrape_result.get('content', result.get('content')),
                    'metadata': {
                        **(result.get('metadata', {})),
                        **(scrape_result.get('metadata', {}))
                    },
                    'scrape_status': 'success',
                    'scraper_used': scrape_result.get('scraper_used')
                })
            else:
                result['scrape_status'] = 'failure'
                scraped_results.append(result)
                
        # Store scraped results in scraper state
        scraper_state['scraped_results'][query_key] = scraped_results
        scraper_state['scrape_successful'] = True
        logger.info(f"Successfully scraped {len(scraped_results)} results for query: {query_key}")
        
    return state
