"""Article Writer Agent functionality."""

import os
import logging
from typing import Dict, List
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from ..prompts import ARTICLE_WRITER_PROMPT
from ..state import State
from ..configuration import Configuration
from ghostwriter.utils.publish.api import fetch_ghost_tags
from ..llm import get_llm 

logger = logging.getLogger(__name__)

async def article_writer_agent(
    state: State,
    config: RunnableConfig
) -> State:
    """
    Agent that processes unique results and generates articles.
    Uses the standard tool pattern with tool-specific state.
    """
    logger.info("=== Starting Article Writer ===")
    
    # Initialize tool state
    if 'article_writer' not in state.tool_states:
        state.tool_states['article_writer'] = {
            'articles': [],
            'generation_successful': False,
            'processed_results': 0,
            'generated_articles': 0,
            'errors': 0
        }
    writer_state = state.tool_states['article_writer']
    
    try:
        # Get unique results from checker tool state
        checker_state = state.tool_states.get('checker', {})
        unique_results = checker_state.get('unique_results', {})
        
        if not unique_results:
            logger.info("No unique results found - ending workflow")
            writer_state['generation_successful'] = False
            return state
            
        configuration = Configuration.from_runnable_config(config)
        model = get_llm(configuration, temperature=0.7)
        
        # Fetch Ghost CMS tags
        app_url = os.getenv("GHOST_APP_URL")
        ghost_api_key = os.getenv("GHOST_API_KEY")
        
        if not app_url or not ghost_api_key:
            raise ValueError("Ghost API credentials not configured")
            
        ghost_tags = await fetch_ghost_tags(app_url, ghost_api_key)
        tag_names = [tag.name for tag in ghost_tags]
        
        articles = []
        
        # Process each unique result
        for query, results in unique_results.items():
            if not isinstance(results, list):
                continue
                
            logger.info(f"Processing query: {query}")
            logger.info(f"Results to process: {len(results)}")
            
            for result in results:
                writer_state['processed_results'] += 1
                url = result.get('url', 'No URL')
                title = result.get('title', 'No title')
                
                logger.info(f"Generating article for: {title}")
                logger.info(f"Source URL: {url}")
                
                try:
                    # Generate article content with tags
                    messages = [
                        SystemMessage(
                            content=ARTICLE_WRITER_PROMPT.format(
                                title=title,
                                content=result.get('content', 'N/A'),
                                tag_names=tag_names
                            )
                        )
                    ]
                    
                    response = await model.ainvoke(messages)
                    article_content = response.content
                    
                    # Store generated article
                    articles.append({
                        'title': title,
                        'content': article_content,
                        'source_url': url,
                        'query': query,
                        'tags': tag_names
                    })
                    writer_state['generated_articles'] += 1
                    
                    logger.info("Article generated successfully")
                    
                except Exception as e:
                    writer_state['errors'] += 1
                    logger.error(f"Error generating article: {str(e)}")
                    continue
        
        # Update state
        writer_state['articles'] = articles
        writer_state['generation_successful'] = True
        
        logger.info("=== Article Writer Summary ===")
        logger.info(f"Processed results: {writer_state['processed_results']}")
        logger.info(f"Generated articles: {writer_state['generated_articles']}")
        logger.info(f"Errors: {writer_state['errors']}")
        logger.info("=== Article Writer Completed ===")

        return state
        
    except Exception as e:
        logger.error(f"Article writer failed: {str(e)}")
        writer_state['generation_successful'] = False
        raise
