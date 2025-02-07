import logging
import os
import psycopg2
from psycopg2.extras import execute_values
import aiohttp
from typing import Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_core.messages import AIMessage

from ...state import State
from .token import generate_ghost_token
from .image_utils import search_images

logger = logging.getLogger(__name__)

def insert_post_to_postgres(title, source_url, published_url):
    """Insert the source_url and published_url into PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
        )
        with conn.cursor() as cursor:
            insert_query = """
                INSERT INTO post_sources (title, source_url, published_url)
                VALUES %s;
            """
            execute_values(cursor, insert_query, [(title, source_url, published_url)])
            conn.commit()
        conn.close()
        logger.info(f"Inserted post into PostgreSQL: {title}")
        return True
    except Exception as e:
        logger.error(f"Error inserting post into PostgreSQL: {str(e)}")
        return False

async def ghost_publisher(
    articles,
    *,
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State,
    publish_status: str = "draft"
) -> bool:
    """Send articles to Ghost CMS and store source_url & published_url in PostgreSQL."""
    logger.info("Starting Ghost Publisher")

    try:
        # Initialize credentials
        ghost_url = os.getenv("GHOST_APP_URL")
        ghost_admin_api_key = os.getenv("GHOST_ADMIN_API_KEY")

        if not all([ghost_url, ghost_admin_api_key]):
            logger.error("Missing Ghost credentials")
            return False

        # Ensure we have a list of articles
        messages = articles if isinstance(articles, list) else articles.get("messages", [])
        published_urls = []

        async with aiohttp.ClientSession() as session:
            for message in messages:
                try:
                    # Extract details
                    title = message.get("title", "Untitled")
                    html_content = message.get("html", "")
                    tags = message.get("tags", [])
                    source_url = message.get("source_url", None)  # Source URL from formatter

                    if not html_content.strip():
                        logger.error(f"Empty HTML content in post: {title}")
                        continue

                    # Fetch images based on title
                    images = await search_images(title)
                    featured_image = images[0]["url"] if images else None

                    # Prepare post data for Ghost API
                    post_data = {
                        "posts": [{
                            "title": title,
                            "html": html_content,
                            "tags": [{"name": tag} for tag in tags],
                            "status": publish_status,
                            "feature_image": featured_image
                        }]
                    }

                    # Send data to Ghost API
                    url = f"{ghost_url}/ghost/api/admin/posts/?source=html"
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
                                "title": title,
                                "tags": tags
                            })
                            logger.info(f"Successfully created Ghost post: {title}")

                            # Store source_url and published_url in PostgreSQL
                            if source_url:
                                insert_post_to_postgres(title, source_url, post_url)
                        else:
                            error_data = await response.text()
                            logger.error(f"Failed to create Ghost post: {response.status} - {error_data}")

                except Exception as e:
                    logger.error(f"Error processing article: {str(e)}")
                    continue

        return published_urls if published_urls else None

    except Exception as e:
        logger.error(f"Unexpected error in Ghost publisher: {str(e)}", exc_info=True)
        return False
