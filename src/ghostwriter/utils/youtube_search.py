"""YouTube search functionality for Ghostwriter."""

import logging
from typing import Dict, List, Optional
from googleapiclient.discovery import build
from langchain_core.runnables import RunnableConfig
from ..configuration import Configuration
from ..state import State

logger = logging.getLogger(__name__)

class YouTubeSearch:
    def __init__(self, api_key: str):
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search YouTube for videos matching the query."""
        try:
            request = self.youtube.search().list(
                q=query,
                part='snippet',
                maxResults=max_results,
                type='video',
                order='relevance'
            )
            response = request.execute()
            
            results = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                video_details = await self.get_video_details(video_id)
                if video_details:
                    results.append(video_details)
            
            return results
        except Exception as e:
            logger.error(f"YouTube search failed for query '{query}': {str(e)}")
            return []

    async def get_video_details(self, video_id: str) -> Optional[Dict[str, str]]:
        """Get detailed information about a YouTube video."""
        try:
            request = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                return None
                
            item = response['items'][0]
            snippet = item['snippet']
            stats = item['statistics']
            
            return {
                'title': snippet['title'],
                'description': snippet['description'],
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'channel': snippet['channelTitle'],
                'published_at': snippet['publishedAt'],
                'duration': item['contentDetails']['duration'],
                'views': stats.get('viewCount', '0'),
                'likes': stats.get('likeCount', '0'),
                'comments': stats.get('commentCount', '0'),
                'thumbnail': snippet['thumbnails']['high']['url']
            }
        except Exception as e:
            logger.error(f"Failed to get details for video {video_id}: {str(e)}")
            return None

async def youtube_search(
    query: str, 
    config: RunnableConfig, 
    state: State
) -> List[Dict[str, str]]:
    """Search YouTube for videos matching the query."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        logger.error("YouTube API key not found in environment variables")
        return []
        
    searcher = YouTubeSearch(api_key)
    configuration = Configuration.from_runnable_config(config)
    return await searcher.search(query, max_results=configuration.max_search_results)
