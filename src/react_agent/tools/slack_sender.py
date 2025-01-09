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

logger = logging.getLogger(__name__)

async def slack_sender(
    articles: Dict[str, List[AIMessage]], 
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> bool:
    """Send articles to a Slack channel with approve/reject buttons."""
    logger.info("Starting Slack Sender")
    
    try:
        # Initialize Slack client
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        slack_channel = os.getenv("SLACK_CHANNEL_ID")
        
        if not slack_token or not slack_channel:
            logger.error("Missing Slack credentials")
            return False
        
        client = WebClient(token=slack_token)
        messages = articles.get("messages", [])
        
        for message in messages:
            content = message.content
            
            # Split content into individual articles and remaining text
            article_parts = []
            remaining_text = content
            
            while "[ARTICLE_START]" in remaining_text and "[ARTICLE_END]" in remaining_text:
                start_idx = remaining_text.find("[ARTICLE_START]")
                end_idx = remaining_text.find("[ARTICLE_END]") + len("[ARTICLE_END]")
                
                if start_idx != -1 and end_idx != -1:
                    article = remaining_text[start_idx:end_idx]
                    article = article.replace("[ARTICLE_START]", "").replace("[ARTICLE_END]", "").strip()
                    article_parts.append(article)
                    remaining_text = remaining_text[end_idx:].strip()
                else:
                    break
            
            # Send each article as a separate message with buttons
            for idx, article in enumerate(article_parts):
                if article.strip():
                    formatted_article = f"```\n{article}\n```"
                    
                    # Create blocks for message with buttons
                    blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": formatted_article
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Approve"
                                    },
                                    "style": "primary",
                                    "action_id": f"approve_article_{idx}",
                                    "value": article  # Store article content in button value
                                },
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Reject"
                                    },
                                    "style": "danger",
                                    "action_id": f"reject_article_{idx}"
                                }
                            ]
                        }
                    ]
                    
                    logger.info(f"Sending article {idx + 1} to Slack")
                    response = client.chat_postMessage(
                        channel=slack_channel,
                        blocks=blocks,
                        text=formatted_article  # Fallback text
                    )
                    if not response["ok"]:
                        logger.error(f"Failed to send article to Slack: {response}")
            
            # Send remaining text as a separate message
            if remaining_text.strip():
                formatted_remaining = f"```\n{remaining_text}\n```"
                logger.info("Sending remaining content to Slack")
                response = client.chat_postMessage(
                    channel=slack_channel,
                    text=formatted_remaining
                )
                if not response["ok"]:
                    logger.error(f"Failed to send remaining content to Slack: {response}")
        
        return True
        
    except SlackApiError as e:
        logger.error(f"Slack API Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in Slack sender: {str(e)}", exc_info=True)
        return False