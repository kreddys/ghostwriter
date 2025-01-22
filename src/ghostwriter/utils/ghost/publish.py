"""Ghost Publisher functionality."""
import logging
from typing import Annotated, Dict, List
import json
import os
import aiohttp
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_core.messages import AIMessage

from ...state import State
from ..notify.slack import send_slack_notification
from .token import generate_ghost_token

logger = logging.getLogger(__name__)

async def ghost_publisher(
    articles: Dict[str, List[AIMessage]], 
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> bool:
    """Send articles to Ghost CMS as drafts."""
    logger.info("Starting Ghost Publisher")
    
    try:
        # Initialize credentials
        ghost_url = os.getenv("GHOST_APP_URL")
        ghost_admin_api_key = os.getenv("GHOST_ADMIN_API_KEY")
        
        if not all([ghost_url, ghost_admin_api_key]):
            logger.error("Missing Ghost credentials")
            return False
        
        messages = articles.get("messages", [])
        
        async with aiohttp.ClientSession() as session:
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
                        
                    # Parse the JSON content
                    data = json.loads(content)
                    posts = data.get("posts", [])
                    
                    for post in posts:
                        # Prepare article data for Ghost API
                        post_data = {
                            "posts": [{
                                "title": post["title"],
                                "lexical": post["lexical"],  # Use the lexical format directly
                                "tags": [{"name": tag} for tag in post.get("tags", [])],
                                "status": "draft"
                            }]
                        }
                        
                        # Send to Ghost API
                        url = f"{ghost_url}/ghost/api/admin/posts/"
                        headers = {
                            "Authorization": f"Ghost {generate_ghost_token(ghost_admin_api_key)}",
                            "Accept-Version": "v5.0",
                            "Content-Type": "application/json"
                        }
                        
                        async with session.post(url, json=post_data, headers=headers) as response:
                            if response.status == 201:  # Successfully created
                                response_data = await response.json()
                                post_url = response_data["posts"][0]["url"]
                                
                                # Send Slack notification
                                await send_slack_notification(
                                    title=post['title'],
                                    tags=post.get('tags', []),
                                    post_url=post_url
                                )
                                logger.info(f"Successfully created Ghost post: {post['title']}")
                            else:
                                error_data = await response.text()
                                logger.error(f"Failed to create Ghost post: {response.status} - {error_data}")
                                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse article JSON: {str(e)}")
                    logger.error(f"Content causing error: {content}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing article: {str(e)}")
                    continue
        
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error in Ghost publisher: {str(e)}", exc_info=True)
        return False