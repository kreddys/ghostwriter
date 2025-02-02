import json
import logging
from typing import Dict
from ..state import State

logger = logging.getLogger(__name__)

def convert_to_lexical(text: str) -> str:
    """
    Converts plain text into a Lexical JSON structure.
    """
    lexical_structure = {
        "root": {
            "children": [
                {"children": [
                    {
                        "detail": 0,
                        "format": 0,
                        "mode": "normal",
                        "style": "",
                        "text": text,
                        "type": "extended-text",
                        "version": 1
                    }
                ],
                "direction": "ltr",
                "format": "",
                "indent": 0,
                "type": "paragraph",
                "version": 1}
            ],
            "direction": "ltr",
            "format": "",
            "indent": 0,
            "type": "root",
            "version": 1
        }
    }
    return json.dumps(lexical_structure)

async def formatter(state: State) -> State:
    """
    Converts plain text articles from article_writer to Lexical format and updates state.
    """
    logger.info("=== Starting Formatter ===")
    
    if 'article_writer' not in state.tool_states:
        logger.info("No articles found to format - ending workflow")
        return state
    
    writer_state = state.tool_states['article_writer']
    articles = writer_state.get('articles', [])
    
    if not articles:
        logger.info("No articles available to format.")
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
            lexical_content = convert_to_lexical(article['content'])
            formatted_articles.append({
                "title": article['title'],
                "lexical": lexical_content,
                "source_url": article['source_url'],
                "tags": article['tags'],
                "query": article['query']
            })
            logger.info(f"Formatted article: {article['title']}")
        except Exception as e:
            formatter_state['errors'] += 1
            logger.error(f"Error formatting article '{article['title']}': {str(e)}")
            continue
    
    formatter_state['formatted_articles'] = formatted_articles
    logger.info(f"Successfully formatted {len(formatted_articles)} articles.")
    
    return state
