"""Supabase URL storage functionality."""
import logging
import json
from typing import Annotated, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_core.messages import AIMessage
from supabase import create_client, Client
import os

from ..state import State

logger = logging.getLogger(__name__)

async def supabase_url_store(
    articles: Dict[str, List[AIMessage]], 
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> bool:
    """Store article URLs in Supabase."""
    logger.info("Starting Supabase URL Store")
    
    try:
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not all([supabase_url, supabase_key]):
            logger.error("Missing Supabase credentials")
            return False
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        messages = articles.get("messages", [])
        logger.info(f"Processing {len(messages)} messages")
        
        for message in messages:
            try:
                # Clean up the content by removing markdown code block markers
                content = message.content.strip()
                if content.startswith("```json"):
                    content = content[7:]  # Remove ```json
                if content.endswith("```"):
                    content = content[:-3]  # Remove ```
                content = content.strip()
                
                if not content:
                    logger.error("Empty content after cleanup")
                    continue
                
                # Log the content before parsing
                logger.debug(f"Attempting to parse content: {content}")
                    
                # Parse the JSON content
                data = json.loads(content)
                posts = data.get("posts", [])
                
                logger.info(f"Found {len(posts)} posts to process")
                
                for post in posts:
                    # Extract title and source URLs
                    title = post.get("title", "untitled")
                    source_urls = post.get("source_urls", [])
                    
                    if source_urls:
                        logger.info(f"Found {len(source_urls)} URLs for article '{title}'")
                        # Insert URLs into Supabase
                        for url in source_urls:
                            data = {
                                "article_title": title,
                                "source_url": url,
                                "created_at": "now()"
                            }
                            
                            logger.debug(f"Inserting data: {data}")
                            result = supabase.table("article_sources").insert(data).execute()
                            
                            if result.data:
                                logger.info(f"Stored URL for article '{title}': {url}")
                            else:
                                logger.error(f"Failed to store URL: {url}")
                    else:
                        logger.warning(f"No source URLs found for article '{title}'")
                            
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse article JSON: {str(e)}")
                logger.error(f"Content causing error: {content}")
                continue
            except Exception as e:
                logger.error(f"Error processing article URLs: {str(e)}")
                continue
        
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error in Supabase URL store: {str(e)}", exc_info=True)
        return False