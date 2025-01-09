"""Slack Sender functionality."""
import logging
from typing import Annotated, Dict, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_core.messages import AIMessage
import os

from ..state import State
from ..configuration import Configuration

logger = logging.getLogger(__name__)

async def slack_sender(
    articles: Dict[str, List[AIMessage]], 
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> bool:
    """Send articles to a Slack channel."""
    logger.info("Starting Slack Sender")
    
    try:
        # Initialize Slack client
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        slack_channel = os.getenv("SLACK_CHANNEL_ID")
        
        if not slack_token or not slack_channel:
            logger.error("Missing Slack credentials - SLACK_BOT_TOKEN or SLACK_CHANNEL_ID not found")
            return False
        
        logger.info(f"Initializing Slack client for channel {slack_channel}")
        client = WebClient(token=slack_token)
        
        # Log the number of articles being processed
        messages = articles.get("messages", [])
        logger.info(f"Processing {len(messages)} messages for Slack")
        
        # Process and send each article
        for i, message in enumerate(messages, 1):
            content = message.content
            article_sections = content.split("===")
            
            logger.info(f"Processing message {i} with {len(article_sections)} sections")
            
            for j, article in enumerate(article_sections, 1):
                if not article.strip():
                    continue
                
                try:
                    # Clean up the article content by removing any remaining tags
                    cleaned_article = article.strip()
                    cleaned_article = cleaned_article.replace("[ARTICLE_START]", "").replace("[ARTICLE_END]", "")
                    cleaned_article = cleaned_article.strip()

                    formatted_message = f"```\n{cleaned_article.strip()}\n```"
                    logger.info(f"Sending article {j} to Slack channel {slack_channel}")
                    
                    response = client.chat_postMessage(
                        channel=slack_channel,
                        text=formatted_message,
                        parse="full"
                    )
                    
                    if response["ok"]:
                        logger.info(f"Successfully sent article {j} to Slack")
                    else:
                        logger.error(f"Failed to send article {j} to Slack: {response}")
                        
                except SlackApiError as e:
                    logger.error(f"Slack API Error for article {j}: {str(e)}")
                    continue
        
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error in Slack sender: {str(e)}", exc_info=True)
        return False