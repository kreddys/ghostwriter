"""Ghost publishing workflow."""
import logging
from langchain_core.runnables import RunnableConfig
from ghostwriter.state import State
from ghostwriter.utils.publish.ghost import ghost_publisher

logger = logging.getLogger(__name__)

async def publish_to_ghost(state: State, config: RunnableConfig) -> State:
    """
    Publish articles to Ghost as drafts using the standard tool pattern.
    """
    logger.info("=== Starting Ghost Publisher ===")
    
    # Initialize tool state
    if 'publisher' not in state.tool_states:
        state.tool_states['publisher'] = {
            'articles_published': 0,
            'articles_failed': 0,
            'publish_successful': False
        }
    pub_state = state.tool_states['publisher']
    
    try:
        # Get formatted articles from formatter state
        formatter_state = state.tool_states.get('formatter', {})
        articles = formatter_state.get('formatted_articles', [])
        
        if not articles:
            logger.info("No formatted articles found to publish")
            pub_state['publish_successful'] = False
            return state
            
        # Publish all articles as drafts
        logger.info(f"Publishing {len(articles)} articles as drafts")
        published_urls = await ghost_publisher(articles, config=config, state=state, publish_status='draft')
        
        if published_urls:
            pub_state['articles_published'] = len(published_urls)
            pub_state['publish_successful'] = True
            pub_state['published_urls'] = published_urls
            logger.info(f"Successfully published {len(published_urls)} articles as drafts")
        else:
            pub_state['articles_failed'] = len(articles)
            logger.error("Failed to publish articles")
            
    except Exception as e:
        logger.error(f"Publisher failed: {str(e)}")
        pub_state['publish_successful'] = False
        raise

    logger.info("=== Publisher Summary ===")
    logger.info(f"Articles published: {pub_state['articles_published']}")
    logger.info(f"Articles failed: {pub_state['articles_failed']}")
    logger.info("=== Publisher Completed ===")
    
    return state
