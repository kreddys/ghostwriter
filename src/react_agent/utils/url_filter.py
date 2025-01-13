"""URL filtering utility."""
import logging
from typing import Dict, List, Any
from supabase import create_client, Client
import os

logger = logging.getLogger(__name__)

async def filter_existing_urls(search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out URLs that already exist in Supabase."""
    logger.info("Starting URL filtering")
    
    try:
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not all([supabase_url, supabase_key]):
            logger.error("Missing Supabase credentials")
            return search_results
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get all existing URLs from Supabase
        response = supabase.table("article_sources").select("source_url").execute()
        existing_urls = {record['source_url'] for record in response.data}
        
        logger.info(f"Found {len(existing_urls)} existing URLs in database")

        incoming_urls = [result.get('url') for result in search_results]
        logger.info(f"Incoming URLs to filter: {incoming_urls}")
        
        # Filter out results with URLs that already exist
        filtered_results = [
            result for result in search_results 
            if result.get('url') not in existing_urls
        ]

        filtered_out_urls = [result.get('url') for result in search_results if result.get('url') in existing_urls]
        remaining_urls = [result.get('url') for result in filtered_results]

        logger.info(f"Filtered out URLs (already exist): {filtered_out_urls}")
        logger.info(f"Remaining unique URLs: {remaining_urls}")

        logger.info(f"Filtered {len(search_results) - len(filtered_results)} existing URLs")

        return filtered_results
        
    except Exception as e:
        logger.error(f"Error filtering URLs: {str(e)}")
        return search_results