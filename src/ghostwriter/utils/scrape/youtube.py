"""YouTube video crawler for fetching transcripts."""

import logging
from typing import Dict, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video URL."""
    parsed = urlparse(url)
    return parsed.netloc in ['www.youtube.com', 'youtube.com'] and 'v' in parse_qs(parsed.query)

def get_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    parsed = urlparse(url)
    if parsed.netloc in ['www.youtube.com', 'youtube.com']:
        query = parse_qs(parsed.query)
        return query.get('v', [None])[0]
    return None

async def scrape_youtube_video(url: str) -> Optional[Dict[str, str]]:
    """Crawl a YouTube video and return its transcript in standardized format."""
    if not is_youtube_url(url):
        return None
        
    video_id = get_video_id(url)
    if not video_id:
        return None
        
    try:
        # Get transcript list
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try English first, then any available language
        try:
            transcript = transcript_list.find_transcript(['en'])
        except:
            transcript = next(iter(transcript_list))
            
        # Fetch and format transcript
        transcript_data = transcript.fetch()
        content = " ".join([t['text'] for t in transcript_data])
        
        # If transcript is not in English, add language info
        language = transcript.language_code
        if language != 'en':
            content = f"[Transcript in {transcript.language}] {content}"
        
        return {
            "url": url,
            "title": f"YouTube Video ({video_id})",  # Added title field
            "content": content,
            "source": "youtube",
            "metadata": {
                "description": "",  # YouTube API would be needed for this
                "language": language,
                "video_id": video_id,
                "status_code": 200 if content else 0
            }
        }
    except Exception as e:
        logger.error(f"Failed to crawl YouTube video {url}: {str(e)}")
        return None