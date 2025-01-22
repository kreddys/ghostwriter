"""YouTube Search functionality."""
import logging
import os
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ...configuration import Configuration
from ...state import State

logger = logging.getLogger(__name__)

async def youtube_search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Search YouTube using the YouTube Data API."""
    logger.info(f"Starting YouTube search for query: {query}")
    
    try:
        configuration = Configuration.from_runnable_config(config)
        
        youtube_api_key = os.getenv("GOOGLE_API_KEY")
        if not youtube_api_key:
            logger.error("Missing YouTube API credentials - API key not found")
            raise ValueError("YouTube API key not found in environment variables")
        
        logger.debug("Building YouTube Data API service")
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)

        search_params = {
            "q": query,
            "part": "snippet",
            "maxResults": configuration.max_search_results,
            "type": "video",
            "order": "relevance"
        }
        
        logger.info(f"Executing YouTube search with max results: {configuration.max_search_results}")
        
        response = youtube.search().list(**search_params).execute()
        logger.debug(f"Raw YouTube API response: {response}")
        
        processed_results = []
        if 'items' in response:
            logger.info(f"Found {len(response['items'])} results from YouTube search")
            for item in response['items']:
                video_id = item['id']['videoId']
                processed_results.append({
                    "type": "video",
                    "title": item['snippet'].get('title', 'N/A'),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "content": item['snippet'].get('description', 'N/A'),
                    "source": "youtube",
                    "thumbnail": item['snippet']['thumbnails']['high']['url']
                })
        else:
            logger.warning("No items found in YouTube search response")
        
        logger.info(f"Successfully processed {len(processed_results)} YouTube search results")
        return processed_results
        
    except HttpError as e:
        logger.error(f"YouTube Search API error: {str(e)}", exc_info=True)
        raise ValueError(f"YouTube Search API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in YouTube search: {str(e)}", exc_info=True)
        raise ValueError(f"Error performing YouTube search: {str(e)}")
