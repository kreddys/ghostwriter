"""Image utilities for Ghost integration."""
import logging
import os
from typing import Dict, List, Optional
import aiohttp
import random

logger = logging.getLogger(__name__)

async def validate_image(url: str) -> bool:
    """Validate an image URL by checking accessibility and dimensions."""
    try:
        async with aiohttp.ClientSession() as session:
            # First check if URL is accessible
            async with session.head(url) as response:
                if response.status != 200:
                    return False
                
                # Check content type
                content_type = response.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    return False
                
            # Get image dimensions
            async with session.get(url) as response:
                if response.status == 200:
                    # Read first few bytes to get dimensions
                    data = await response.content.read(1024)
                    if b"JFIF" in data or b"PNG" in data or b"GIF" in data:
                        return True
        return False
    except Exception as e:
        logger.error(f"Image validation error: {str(e)}")
        return False

async def search_google_images(query: str, num_results: int = 3) -> Optional[List[Dict]]:
    """Search for images using Google Custom Search API."""
    api_key = os.getenv("GOOGLE_CSE_API_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    
    if not api_key or not cx:
        logger.warning("Google CSE API key or CX not configured")
        return None
        
    url = "https://customsearch.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "searchType": "image",
        "num": num_results,
        "imgSize": "large",
        "imgType": "photo",
        "safe": "active",
        "key": api_key,
        "cx": cx
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    valid_images = []
                    
                    # Validate each image
                    for item in data.get("items", []):
                        image_url = item["link"]
                        if await validate_image(image_url):
                            valid_images.append({
                                "url": image_url,
                                "title": item.get("title", ""),
                                "width": item["image"]["width"],
                                "height": item["image"]["height"],
                                "source": "google"
                            })
                            if len(valid_images) >= num_results:
                                break
                    
                    return valid_images
                else:
                    logger.error(f"Google CSE API error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error searching Google images: {str(e)}")
        return None

async def trigger_unsplash_download(image_url: str) -> None:
    """Trigger Unsplash download event for proper attribution."""
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        return
        
    try:
        async with aiohttp.ClientSession() as session:
            download_url = f"https://api.unsplash.com/photos/{image_url.split('/')[-1]}/download"
            headers = {"Authorization": f"Client-ID {access_key}"}
            async with session.get(download_url, headers=headers):
                pass  # We just need to trigger the download, don't need the response
    except Exception as e:
        logger.error(f"Error triggering Unsplash download: {str(e)}")

async def search_unsplash_images(query: str, num_results: int = 3) -> Optional[List[Dict]]:
    """Search for images using Unsplash API."""
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    
    if not access_key:
        logger.warning("Unsplash access key not configured")
        return None
        
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": num_results,
        "orientation": "landscape"
    }
    headers = {
        "Authorization": f"Client-ID {access_key}"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    valid_images = []
                    
                    # Process Unsplash results
                    for item in data.get("results", []):
                        image_url = item["urls"]["regular"]
                        if await validate_image(image_url):
                            # Trigger download for proper attribution
                            await trigger_unsplash_download(image_url)
                            
                            valid_images.append({
                                "url": image_url,
                                "title": item.get("description", item.get("alt_description", "")),
                                "width": item["width"],
                                "height": item["height"],
                                "source": "unsplash",
                                "attribution": f"Photo by {item['user']['name']} on Unsplash ({item['user']['links']['html']})",
                                "user_url": item["user"]["links"]["html"],
                                "license": item.get("links", {}).get("html", "")
                            })
                            if len(valid_images) >= num_results:
                                break
                    
                    return valid_images
                else:
                    logger.error(f"Unsplash API error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error searching Unsplash images: {str(e)}")
        return None

async def search_images(query: str, num_results: int = 3) -> Optional[List[Dict]]:
    """Search for images from multiple sources."""
    # Get images from both sources
    google_images = await search_google_images(query, num_results) or []
    unsplash_images = await search_unsplash_images(query, num_results) or []
    
    # Combine and shuffle results
    all_images = google_images + unsplash_images
    random.shuffle(all_images)
    
    # Return up to requested number of images
    return all_images[:num_results]
