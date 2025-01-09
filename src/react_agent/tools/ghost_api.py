from typing import List
import aiohttp
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GhostTag:
    id: str
    name: str
    slug: str
    url: str

async def fetch_ghost_tags(app_url: str, api_key: str) -> List[GhostTag]:
    """
    Fetch all tags from Ghost CMS API, handling pagination.
    
    Args:
        app_url (str): Base URL of the Ghost CMS instance
        api_key (str): Ghost Content API key
        
    Returns:
        List[GhostTag]: List of all available tags
    """
    all_tags = []
    page = 1
    
    if not app_url:
        raise ValueError("APP_URL is not configured")
    
    if not api_key:
        raise ValueError("Ghost API key is not configured")
    
    async with aiohttp.ClientSession() as session:
        while True:
            # Include the API key in the URL
            url = f"{app_url}/ghost/api/content/tags/?key={api_key}&page={page}"
            
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch tags: {response.status}")
                        break
                    
                    data = await response.json()
                    tags = data.get('tags', [])
                    if not tags:
                        break
                    
                    # Convert raw tags to GhostTag objects
                    for tag in tags:
                        ghost_tag = GhostTag(
                            id=tag['id'],
                            name=tag['name'],
                            slug=tag['slug'],
                            url=tag['url']
                        )
                        all_tags.append(ghost_tag)
                    
                    # Check if there are more pages
                    pagination = data.get('meta', {}).get('pagination', {})
                    if not pagination.get('next'):
                        break
                    
                    page += 1
                    
            except Exception as e:
                logger.error(f"Error fetching tags: {e}")
                break
    
    logger.info(f"Fetched {len(all_tags)} tags from Ghost CMS")
    return all_tags

@dataclass
class GhostArticle:
    id: str
    title: str
    content: str
    url: str

async def fetch_ghost_articles(app_url: str, api_key: str) -> List[GhostArticle]:
    """Fetch all articles from Ghost CMS API."""
    all_articles = []
    page = 1
    
    async with aiohttp.ClientSession() as session:
        while True:
            url = f"{app_url}/ghost/api/content/posts/?key={api_key}&page={page}&limit=100&formats=html"
            
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        break
                    
                    data = await response.json()
                    posts = data.get('posts', [])
                    if not posts:
                        break
                    
                    for post in posts:
                        ghost_article = GhostArticle(
                            id=post['id'],
                            title=post['title'],
                            content=post.get('html', ''),
                            url=post['url']
                        )
                        all_articles.append(ghost_article)
                    
                    if not data.get('meta', {}).get('pagination', {}).get('next'):
                        break
                    
                    page += 1
                    
            except Exception as e:
                logger.error(f"Error fetching articles: {e}")
                break
    
    return all_articles