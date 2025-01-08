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
    """
    Send articles to a Slack channel.
    
    Args:
        articles: Dictionary containing articles as AIMessages
        config: Configuration for the tool
        state: Current state
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Starting Slack Sender")
    
    try:
        # Initialize Slack client
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        slack_channel = os.getenv("SLACK_CHANNEL_ID")
        
        if not slack_token or not slack_channel:
            logger.error("Missing Slack credentials")
            raise ValueError("Slack token or channel ID not found in environment variables")
        
        client = WebClient(token=slack_token)
        
        # Process and send each article
        for message in articles.get("messages", []):
            content = message.content
            
            # Split content into individual articles
            article_sections = content.split("===")
            
            for article in article_sections:
                if not article.strip():
                    continue
                
                try:
                    # Format the message for Slack
                    formatted_message = f"```\n{article.strip()}\n```"
                    
                    # Send message to Slack
                    response = client.chat_postMessage(
                        channel=slack_channel,
                        text=formatted_message,
                        parse="full"
                    )
                    
                    if response["ok"]:
                        logger.info(f"Successfully sent article to Slack channel {slack_channel}")
                    else:
                        logger.error(f"Failed to send article to Slack: {response}")
                        
                except SlackApiError as e:
                    logger.error(f"Error sending message to Slack: {str(e)}")
                    continue
        
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error in Slack sender: {str(e)}", exc_info=True)
        raise ValueError(f"Error sending articles to Slack: {str(e)}")