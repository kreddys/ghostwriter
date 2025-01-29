"""Utility for scraping content using Firecrawl API."""

import os
import logging
import aiohttp
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)

def clean_content(content: str) -> str:
    """Clean scraped content to remove navigation, scripts and other UI elements."""
    
    # Remove navigation menus and links
    patterns_to_remove = [
        r'\[.*?\]\(.*?\)',  # Remove markdown links
        r'- \[.*?\].*?\n',  # Remove navigation items
        r'!\[.*?\].*?\n',   # Remove images
        r'Copyright ©.*?\n', # Remove copyright notices
        r'Share.*?\n',      # Remove share buttons
        r'Follow Us.*?\n',  # Remove social media links
        r'Click to.*?\n',   # Remove UI instructions
        r'Sign in.*?\n',    # Remove sign in elements
        r'Subscribe.*?\n',  # Remove subscription prompts
        r'More from.*?\n',  # Remove additional content sections
        r'Explore.*?\n',    # Remove exploration sections
        r'Get Current Updates.*?\n', # Remove update prompts
    ]
    
    cleaned_content = content
    for pattern in patterns_to_remove:
        cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.MULTILINE)
    
    # Remove empty lines and excessive whitespace
    cleaned_content = '\n'.join(
        line.strip() for line in cleaned_content.splitlines() 
        if line.strip()
    )
    
    return cleaned_content

async def firecrawl_scrape_url(url: str) -> Optional[Dict]:
    """
    Scrape content from a URL using Firecrawl API.
    Returns data in standardized format.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.error("FIRECRAWL_API_KEY environment variable not set")
        raise ValueError("Firecrawl API key is required")

    api_url = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1/scrape")
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
                
                content_data = data.get("data", {})
                metadata = content_data.get("metadata", {})
                
                raw_content = content_data.get("markdown", "No content available")
                cleaned_content = clean_content(raw_content)
                
                return {
                    "url": url,
                    "title": metadata.get("title", "No Title"),
                    "content": cleaned_content,
                    "source": "firecrawl",
                    "metadata": {
                        "description": metadata.get("description", ""),
                        "language": metadata.get("language", ""),
                        "status_code": metadata.get("statusCode", 0)
                    }
                }
                
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {str(e)}")
        return None
