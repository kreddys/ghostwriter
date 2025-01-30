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
    """Execute scraping process."""
    logger.info("Starting scrape process")
    
    # Initialize scraper state
    if 'scraper' not in state.tool_states:
        state.tool_states['scraper'] = {
            'scraped_results': {},
            'scrape_successful': False
        }
    scraper_state = state.tool_states['scraper']

    try:
        # Get search results
        searcher_state = state.tool_states.get('searcher', {})
        search_results = searcher_state.get('search_results', {})
        
        if not search_results:
            logger.warning("No search results to scrape")
            scraper_state['scrape_successful'] = False
            return state

        # Process each query's results
        for query, results in search_results.items():
            if not isinstance(results, list):
                continue
                
            logger.info(f"Attempting to scrape URLs for query: {query}")
            scraped_results = await scrape_multiple_urls(
                [result['url'] for result in results],
                Configuration.from_runnable_config(config)
            )
            
            # Add this check to stop if no valid results
            if not scraped_results or all(not result.get('content') for result in scraped_results):
                logger.error("No valid content obtained from scraping")
                scraper_state['scrape_successful'] = False
                return state
                
            scraper_state['scraped_results'][query] = scraped_results
            logger.info(f"Successfully scraped {len(scraped_results)} results for query: {query}")
            
        scraper_state['scrape_successful'] = True
        return state
        
    except Exception as e:
        logger.error(f"Error in scraping process: {str(e)}")
        scraper_state['scrape_successful'] = False
        return state
