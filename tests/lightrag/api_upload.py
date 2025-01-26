import requests
import os
import logging
import asyncio
from ghostwriter.utils.publish.api import fetch_ghost_articles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
LIGHTRAG_API_URL = "http://localhost:9621"  # Replace with your LightRAG API URL
GHOST_CMS_API_URL = os.getenv("GHOST_APP_URL")  # Ghost CMS URL from environment variable
GHOST_API_KEY = os.getenv("GHOST_API_KEY")  # Ghost CMS API key from environment variable

def upload_articles_to_lightrag():
    """
    Fetch articles from Ghost CMS and upload them to LightRAG.
    """
    # Ensure Ghost credentials are configured
    if not all([GHOST_CMS_API_URL, GHOST_API_KEY]):
        logger.warning("Ghost credentials not configured. Please set GHOST_APP_URL and GHOST_API_KEY.")
        return

    # Fetch articles from the Ghost CMS API
    try:
        logger.info("Fetching articles from Ghost CMS...")
        # Use asyncio to run the async fetch_ghost_articles function
        articles = asyncio.run(fetch_ghost_articles(GHOST_CMS_API_URL, GHOST_API_KEY))
        logger.info(f"Fetched {len(articles)} articles from Ghost CMS.")
    except Exception as e:
        logger.error(f"Failed to fetch articles from Ghost CMS: {str(e)}")
        return

    # Upload each article to LightRAG via the API
    for article in articles:
        try:
            # Prepare the text content for insertion
            text_content = f"Title: {article.title}\nContent: {article.content}"
            
            # Make a POST request to the /documents/text endpoint
            logger.info(f"Uploading article: {article.title}")
            response = requests.post(
                f"{LIGHTRAG_API_URL}/documents/text",
                json={
                    "text": text_content,
                    "description": f"Article {article.id} from Ghost CMS"
                }
            )
            
            # Check if the request was successful
            if response.status_code == 200 and response.json().get("status") == "success":
                logger.info(f"Successfully uploaded article: {article.title}")
            else:
                logger.error(f"Failed to upload article {article.title}. Response: {response.json()}")
        
        except Exception as e:
            logger.error(f"Error uploading article {article.title}: {str(e)}")
            continue

    # Verify that all articles were uploaded
    logger.info(f"Total articles uploaded: {len(articles)}")

if __name__ == "__main__":
    upload_articles_to_lightrag()