"""URL filtering functionality for processing search results."""

import os
import logging
from typing import Dict, List, Any, Set
from urllib.parse import urlparse
from supabase import create_client, Client
from dataclasses import dataclass
from difflib import SequenceMatcher

from .state import State

logger = logging.getLogger(__name__)

@dataclass
class DomainStats:
    """Track statistics for each domain."""
    count: int = 0
    urls: Set[str] = None
    
    def __post_init__(self):
        if self.urls is None:
            self.urls = set()

def normalize_url(url: str) -> str:
    """Normalize URL by removing common variations."""
    try:
        # Remove protocol
        url = url.replace("http://", "").replace("https://", "")
        # Remove www
        url = url.replace("www.", "")
        # Remove trailing slash
        url = url.rstrip("/")
        # Remove query parameters
        url = url.split("?")[0]
        # Remove index.php and similar
        url = url.replace("index.php/", "")
        # Remove common tracking parameters
        url = url.split("#")[0]
        return url.lower()
    except Exception as e:
        logger.error(f"Error normalizing URL {url}: {str(e)}")
        return url

def get_domain(url: str) -> str:
    """Extract main domain from URL."""
    try:
        parsed = urlparse(url if url.startswith(('http://', 'https://')) else f'https://{url}')
        domain_parts = parsed.netloc.split('.')
        # Handle cases like city.timesofindia.com
        if len(domain_parts) > 2:
            return '.'.join(domain_parts[-2:])
        return parsed.netloc
    except Exception as e:
        logger.error(f"Error extracting domain from URL {url}: {str(e)}")
        return url

def calculate_url_similarity(url1: str, url2: str) -> float:
    """Calculate similarity between two URLs."""
    return SequenceMatcher(None, normalize_url(url1), normalize_url(url2)).ratio()

async def filter_existing_urls(
    search_results: Dict[str, List[Dict[str, Any]]],
    state: State,
    max_articles_per_domain: int = 3,
    url_similarity_threshold: float = 0.85
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Filter out URLs that already exist in Supabase with enhanced filtering.
    
    Args:
        search_results: Dictionary of search results grouped by query
        state: Current application state
        max_articles_per_domain: Maximum number of articles allowed from the same domain
        url_similarity_threshold: Threshold for URL similarity matching
    
    Returns:
        Dictionary of filtered search results
    """
    logger.info("Starting enhanced URL filtering process")
    
    try:
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not all([supabase_url, supabase_key]):
            logger.error("Missing Supabase credentials")
            return search_results
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get existing URLs from Supabase
        response = supabase.table("article_sources").select("source_url").execute()
        existing_urls = {normalize_url(record['source_url']) for record in response.data}
        
        logger.info(f"Found {len(existing_urls)} existing URLs in database")
        
        filtered_results = {}
        domain_stats = {}
        
        # Process each query's results
        for query, results in search_results.items():
            filtered_query_results = []
            
            for result in results:
                url = result.get('url', '')
                if not url:
                    continue
                    
                normalized_url = normalize_url(url)
                domain = get_domain(url)
                
                # Initialize domain stats if not exists
                if domain not in domain_stats:
                    domain_stats[domain] = DomainStats()
                
                # Check if URL is too similar to existing ones
                is_duplicate = False
                for existing_url in existing_urls:
                    if calculate_url_similarity(normalized_url, existing_url) >= url_similarity_threshold:
                        is_duplicate = True
                        break
                
                # Check if URL is too similar to already processed ones
                for processed_url in domain_stats[domain].urls:
                    if calculate_url_similarity(normalized_url, processed_url) >= url_similarity_threshold:
                        is_duplicate = True
                        break
                
                if not is_duplicate and domain_stats[domain].count < max_articles_per_domain:
                    filtered_query_results.append(result)
                    domain_stats[domain].count += 1
                    domain_stats[domain].urls.add(normalized_url)
                    logger.info(f"Accepted new URL: {url} from domain: {domain}")
                else:
                    logger.info(f"Filtered out URL: {url} " + 
                              f"(duplicate: {is_duplicate}, " +
                              f"domain count: {domain_stats[domain].count})")
            
            if filtered_query_results:
                filtered_results[query] = filtered_query_results
        
        # Log statistics
        total_domains = len(domain_stats)
        total_accepted = sum(stats.count for stats in domain_stats.values())
        logger.info(f"Filtering complete: {total_accepted} URLs accepted across {total_domains} domains")
        
        # Store filtered results in state
        state.url_filtered_results = filtered_results
        
        return filtered_results
        
    except Exception as e:
        logger.error(f"Error in URL filtering: {str(e)}")
        return search_results