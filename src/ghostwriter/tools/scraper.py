"""Utilities for crawling content using multiple configured crawlers."""

import logging
from typing import Dict, List, Optional
from ..configuration import Configuration
from ..utils.scrape.firecrawl import firecrawl_scrape_url
from ..utils.scrape.youtube import crawl_youtube_video

logger = logging.getLogger(__name__)

# Define crawler mapping here
CRAWLER_MAPPING = {
    "firecrawl": firecrawl_scrape_url,
    "youtube": crawl_youtube_video
}

async def crawl_with_fallback(
    url: str, 
    config: Configuration,
    crawler_mapping: Dict = CRAWLER_MAPPING
) -> Optional[Dict]:
    """
    Attempt to crawl a URL using configured crawlers in sequence.
    
    Args:
        url: The URL to crawl
        config: Configuration object
        crawler_mapping: Dictionary mapping crawler names to their functions
        
    Returns:
        Dictionary containing crawled content or None if all crawlers failed
    """
    active_crawlers = config.crawling_engines
    if not active_crawlers:  # If empty, use all available crawlers
        active_crawlers = list(crawler_mapping.keys())
    
    logger.info(f"Attempting to crawl {url} with crawlers: {active_crawlers}")
    
    for crawler_name in active_crawlers:
        crawler_func = crawler_mapping.get(crawler_name)
        if not crawler_func:
            logger.warning(f"Unknown crawler: {crawler_name}")
            continue
            
        try:
            logger.info(f"Trying {crawler_name} for URL: {url}")
            result = await crawler_func(url)
            if result:
                logger.info(f"Successfully crawled with {crawler_name}")
                return {
                    **result,
                    "crawler_used": crawler_name,
                    "scrape_status": "success"
                }
            logger.warning(f"{crawler_name} failed for URL: {url}")
        except Exception as e:
            logger.error(f"Error with {crawler_name} for URL {url}: {str(e)}")
            
    logger.warning(f"All crawlers failed for URL: {url}")
    return {
        "url": url,
        "scrape_status": "failure"
    }

async def crawl_multiple_urls(
    urls: List[str],
    config: Configuration,
    crawler_mapping: Dict = CRAWLER_MAPPING
) -> List[Dict]:
    """
    Crawl multiple URLs using configured crawlers with fallback logic.
    
    Args:
        urls: List of URLs to crawl
        config: Configuration object
        crawler_mapping: Dictionary mapping crawler names to their functions
        
    Returns:
        List of crawled results (successful and failed)
    """
    results = []
    
    for url in urls:
        result = await crawl_with_fallback(url, config, crawler_mapping)
        results.append(result)
            
    return results

async def update_results_with_crawler_data(
    results: List[Dict],
    config: Configuration,
    crawler_mapping: Dict = CRAWLER_MAPPING
) -> List[Dict]:
    """
    Update search results with crawled content.
    
    Args:
        results: List of search results to update
        config: Configuration object
        crawler_mapping: Dictionary mapping crawler names to their functions
        
    Returns:
        List of updated results
    """
    # Get URLs to crawl
    urls = [result.get('url') for result in results if result.get('url')]
    
    # Crawl URLs using the utility
    crawled_data = await crawl_multiple_urls(urls, config, crawler_mapping)
    
    # Create URL to crawled data mapping
    crawled_data_map = {data['url']: data for data in crawled_data if data}
    
    # Update original results with crawled data
    updated_results = []
    for result in results:
        url = result.get('url')
        if not url:
            result['scrape_status'] = 'failure'
            updated_results.append(result)
            continue
            
        crawl_result = crawled_data_map.get(url)
        if crawl_result and crawl_result.get('scrape_status') == 'success':
            updated_results.append({
                **result,
                'title': crawl_result.get('title', result.get('title')),
                'content': crawl_result.get('content', result.get('content')),
                'metadata': {
                    **(result.get('metadata', {})),
                    **(crawl_result.get('metadata', {}))
                },
                'scrape_status': 'success',
                'crawler_used': crawl_result.get('crawler_used')
            })
        else:
            result['scrape_status'] = 'failure'
            updated_results.append(result)
            
    return updated_results
