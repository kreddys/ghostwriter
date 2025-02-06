import json
import logging
from typing import Dict
from bs4 import BeautifulSoup
from ..state import State

logger = logging.getLogger(__name__)

async def formatter(state: State) -> State:
    """
    Processes HTML articles from article_writer and updates state.
    """
    logger.info("=== Starting Formatter ===")
    
    if 'article_writer' not in state.tool_states:
        logger.info("No articles found to process - ending workflow")
        return state
    
    writer_state = state.tool_states['article_writer']
    articles = writer_state.get('articles', [])
    
    if not articles:
        logger.info("No articles available to process.")
        return state
    
    # Initialize formatter tool state
    if 'formatter' not in state.tool_states:
        state.tool_states['formatter'] = {
            'formatted_articles': [],
            'errors': 0
        }
    formatter_state = state.tool_states['formatter']
    
    formatted_articles = []
    for article in articles:
        try:
            # Clean and structure the HTML content using BeautifulSoup
            soup = BeautifulSoup(article['content'], "html.parser")
            
            # Remove all <h1> tags from the content
            for h1_tag in soup.find_all('h1'):
                h1_tag.extract()
            
            html_content = str(soup.prettify())
            
            formatted_articles.append({
                "title": article['title'],
                "html": html_content,
                "source_url": article['source_url'],
                "tags": article['tags'],
                "query": article['query']
            })
            logger.info(f"Processed article: {article['title']}")
        except Exception as e:
            formatter_state['errors'] += 1
            logger.error(f"Error processing article '{article['title']}': {str(e)}")
            continue
    
    formatter_state['formatted_articles'] = formatted_articles
    logger.info(f"Successfully processed {len(formatted_articles)} articles.")
    
    return state
