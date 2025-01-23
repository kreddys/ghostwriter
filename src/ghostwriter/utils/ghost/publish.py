"""Ghost Publisher functionality."""
import logging
from typing import Annotated, Dict, List, Union
import json
import os
import aiohttp
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_core.messages import AIMessage

from ...state import State
from .token import generate_ghost_token
from .image_utils import search_images

logger = logging.getLogger(__name__)

async def ghost_publisher(
    articles: Union[Dict[str, List[AIMessage]], List[AIMessage]], 
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State,
    publish_status: str = "draft"
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
        
        # Handle both dict and list input formats
        messages = articles if isinstance(articles, list) else articles.get("messages", [])
        published_urls = []
        
        async with aiohttp.ClientSession() as session:
            for message in messages:
                try:
                    # Handle both AIMessage and dict formats
                    if hasattr(message, 'content'):
                        content = message.content.strip()
                    else:
                        content = message.get('content', '').strip()
                    
                    # Clean up the content by removing markdown code block markers
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
                        # Search for relevant images using the post title
                        images = await search_images(post["title"])
                        featured_image = images[0]["url"] if images else None
                        
                        # Prepare article data for Ghost API
                        post_data = {
                            "posts": [{
                                "title": post["title"],
                                "lexical": post["lexical"],  # Use the lexical format directly
                                "tags": [{"name": tag} for tag in post.get("tags", [])],
                                "status": publish_status,
                                "feature_image": featured_image["url"] if featured_image and isinstance(featured_image, dict) else featured_image,
                                "feature_image_caption": featured_image.get("attribution") if featured_image and isinstance(featured_image, dict) else None,
                                "feature_image_alt": featured_image.get("title", "") if featured_image and isinstance(featured_image, dict) else "",
                                "codeinjection_foot": f"<div style='margin-top: 2rem; font-size: 0.875rem; color: #666;'>Originally sourced from: <a href='{state.tool_states['searcher']['search_results'][list(state.tool_states['searcher']['search_results'].keys())[0]][0]['url']}' target='_blank' rel='noopener'>{state.tool_states['searcher']['search_results'][list(state.tool_states['searcher']['search_results'].keys())[0]][0]['url']}</a></div>" if state.tool_states.get('searcher', {}).get('search_results') else None
                            }]
                        }
                        
                        # Add attribution to lexical content if using Unsplash image
                        if featured_image and isinstance(featured_image, dict) and featured_image.get("source") == "unsplash":
                            try:
                                lexical_data = json.loads(post_data["posts"][0]["lexical"])
                                # Create attribution paragraph with link
                                attribution_node = {
                                    "children": [{
                                        "detail": 0,
                                        "format": 0,
                                        "mode": "normal",
                                        "style": "",
                                        "text": "Image credit: ",
                                        "type": "text",
                                        "version": 1
                                    }, {
                                        "detail": 0,
                                        "format": 1,  # Link format
                                        "mode": "normal",
                                        "style": "",
                                        "text": featured_image["attribution"],
                                        "type": "link",
                                        "version": 1,
                                        "url": featured_image["user_url"]
                                    }],
                                    "direction": "ltr",
                                    "format": "",
                                    "indent": 0,
                                    "type": "paragraph",
                                    "version": 1
                                }
                                # Add attribution at the end of the content
                                if "children" in lexical_data["root"]:
                                    lexical_data["root"]["children"].append(attribution_node)
                                post_data["posts"][0]["lexical"] = json.dumps(lexical_data)
                            except Exception as e:
                                logger.error(f"Error adding attribution to lexical content: {str(e)}")
                        
                        if featured_image:
                            logger.info(f"Using featured image: {featured_image}")
                        
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
                                published_urls.append({
                                    "url": post_url,
                                    "title": post["title"],
                                    "tags": post.get("tags", [])
                                })
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
        
        return published_urls if published_urls else None
        
    except Exception as e:
        logger.error(f"Unexpected error in Ghost publisher: {str(e)}", exc_info=True)
        return False
