"""Utility for scraping content using Firecrawl API."""

import os
import logging
import aiohttp
from typing import Dict, Optional

logger = logging.getLogger(__name__)

async def scrape_url_content(url: str) -> Optional[Dict]:
    """
    Scrape content from a URL using Firecrawl API.
    
    Args:
        url (str): The URL to scrape
        
    Returns:
        Optional[Dict]: Dictionary containing scraped content or None if failed
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.error("FIRECRAWL_API_KEY environment variable not set")
        return None

    api_url = "https://api.firecrawl.dev/v1/scrape"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "url": url,
        "formats": ["markdown", "html"],
        "actions": [
            {"type": "wait", "milliseconds": 2000},
            {"type": "scrape"}
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Firecrawl API error: {response.status}")
                    return None
                    
                data = await response.json()
                
                if not data.get("success"):
                    logger.error(f"Firecrawl API returned error: {data}")
                    return None
                
                # Extract relevant data from response
                content_data = data.get("data", {})
                metadata = content_data.get("metadata", {})
                
                result = {
                    "url": url,
                    "title": metadata.get("title", "No Title"),
                    "content": content_data.get("markdown", "No content available"),
                    "source": "direct_input",
                    "metadata": {
                        "description": metadata.get("description", ""),
                        "language": metadata.get("language", ""),
                        "og_title": metadata.get("ogTitle", ""),
                        "og_description": metadata.get("ogDescription", ""),
                        "status_code": metadata.get("statusCode", 0)
                    }
                }
                
                logger.info(f"Successfully scraped content from URL: {url}")
                return result
                
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {str(e)}")
        return None