"""Slack Sender functionality."""
import logging
import json
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
            try:
                # Parse the JSON array of articles from the message content
                article_list = json.loads(message.content)
                
                # Send each article as a separate message with buttons
                for idx, article in enumerate(article_list):
                    # Format the article content for Slack
                    article_text = (
                        f"*Title:* {article['title']}\n\n"
                        f"*Excerpt:* {article['excerpt']}\n\n"
                        f"*Tags:* {', '.join(article['tags'])}\n\n"
                        f"*Content:*\n{article['html']}"
                    )
                    
                    # Create blocks for message with buttons
                    blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": article_text[:3000]  # Slack has a text limit
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
                                    "value": json.dumps({
                                        "title": article["title"],
                                        "tags": article["tags"]
                                    })  # Store minimal article info in button value
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
                    
                    logger.info(f"Sending article {idx + 1} to Slack: {article['title']}")
                    response = client.chat_postMessage(
                        channel=slack_channel,
                        blocks=blocks,
                        text=f"New article: {article['title']}"  # Fallback text
                    )
                    
                    if not response["ok"]:
                        logger.error(f"Failed to send article to Slack: {response}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse article JSON: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Error processing article: {str(e)}")
                continue
        
        return True
        
    except SlackApiError as e:
        logger.error(f"Slack API Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in Slack sender: {str(e)}", exc_info=True)
        return False