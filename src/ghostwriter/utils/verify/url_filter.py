import logging
import os
from typing import Dict, List, Any
import psycopg2
from psycopg2.extras import DictCursor

logger = logging.getLogger(__name__)

def get_existing_urls() -> set:
    """Retrieve existing URLs from PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
        )
        
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT source_url FROM post_sources;")
            existing_urls = {row["source_url"] for row in cursor.fetchall()}
        
        conn.close()
        return existing_urls
    
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return set()

def filter_existing_urls(search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out URLs that already exist in PostgreSQL."""
    logger.info("Starting URL filtering")
    
    existing_urls = get_existing_urls()
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
