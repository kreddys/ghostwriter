"""Slack notification functionality."""
import logging
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

async def send_slack_notification(title: str, tags: list, post_url: str) -> bool:
    """Send a Slack notification about a new Ghost draft post."""
    try:
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        slack_channel = os.getenv("SLACK_CHANNEL_ID")
        
        if not all([slack_token, slack_channel]):
            logger.error("Missing Slack credentials")
            return False
            
        client = WebClient(token=slack_token)
        
        notification_text = (
            f"*New draft article created in Ghost*\n"
            f"*Title:* {title}\n"
            f"*Tags:* {', '.join(tags)}\n"
            f"*Preview URL:* {post_url}\n\n"
            "Please review and publish the article in Ghost CMS."
        )
        
        response = client.chat_postMessage(
            channel=slack_channel,
            text=notification_text,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": notification_text
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View in Ghost"
                            },
                            "url": post_url,
                            "action_id": "view_ghost_article"
                        }
                    ]
                }
            ]
        )
        
        if not response["ok"]:
            logger.error(f"Failed to send Slack notification: {response}")
            return False
            
        return True
        
    except SlackApiError as e:
        logger.error(f"Slack API Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in Slack notifier: {str(e)}")
        return False