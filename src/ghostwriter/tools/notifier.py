"""Notification tool for sending Slack messages."""
import logging
from langchain_core.runnables import RunnableConfig
from ghostwriter.state import State
from ghostwriter.utils.notify.slack import send_slack_notification

logger = logging.getLogger(__name__)

async def notify(state: State, config: RunnableConfig) -> State:
    """
    Send notifications using the standard tool pattern.
    """
    logger.info("=== Starting Notifier ===")
    
    # Initialize tool state
    if 'notify' not in state.tool_states:
        state.tool_states['notify'] = {
            'notifications_sent': 0,
            'notifications_failed': 0,
            'notify_successful': False
        }
    notify_state = state.tool_states['notify']
    
    try:
        # Get published articles from publisher state
        pub_state = state.tool_states.get('publisher', {})
        published_urls = pub_state.get('published_urls', [])
        
        if not published_urls:
            logger.info("No published articles found to notify")
            notify_state['notify_successful'] = True
            return state
            
        # Send notifications for each published article
        logger.info(f"Sending notifications for {len(published_urls)} articles")
        
        for url in published_urls:
            try:
                await send_slack_notification(
                    title=url.get('title'),
                    tags=url.get('tags', []),
                    post_url=url.get('url')
                )
                notify_state['notifications_sent'] += 1
            except Exception as e:
                logger.error(f"Failed to send notification: {str(e)}")
                notify_state['notifications_failed'] += 1
                
        notify_state['notify_successful'] = True
        
    except Exception as e:
        logger.error(f"Notifier failed: {str(e)}")
        notify_state['notify_successful'] = False
        raise

    logger.info("=== Notifier Summary ===")
    logger.info(f"Notifications sent: {notify_state['notifications_sent']}")
    logger.info(f"Notifications failed: {notify_state['notifications_failed']}")
    logger.info("=== Notifier Completed ===")
    
    return state
