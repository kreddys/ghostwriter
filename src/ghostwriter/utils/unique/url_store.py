"""URL storage workflow."""
import logging
from langchain_core.runnables import RunnableConfig
from ghostwriter.state import State
from ghostwriter.utils.unique.url_store_supabase import supabase_url_store

logger = logging.getLogger(__name__)

async def store_urls(state: State, config: RunnableConfig) -> State:
    """Store article URLs in Supabase."""
    logger.info("Starting Supabase URL storage process")
    
    try:
        if hasattr(state, 'articles') and state.articles:
            logger.info(f"Found {len(state.articles.get('messages', []))} articles to store URLs")
            success = await supabase_url_store(state.articles, config=config, state=state)
            if success:
                logger.info("Successfully stored URLs in Supabase")
            else:
                logger.error("Failed to store URLs in Supabase")
        else:
            logger.warning("No articles found in state to store URLs")
    except Exception as e:
        logger.error(f"Error storing URLs in Supabase: {str(e)}")
        
    return state
