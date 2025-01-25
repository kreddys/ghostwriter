"""Utility functions for uniqueness checking using LightRAG."""
import logging
import os
from typing import Dict
from ghostwriter.utils.unique.lightrag_ui import LightRAG, QueryParam
from ghostwriter.configuration import Configuration
from ghostwriter.utils.publish.api import fetch_ghost_articles

logger = logging.getLogger(__name__)

async def init_lightrag_with_ghost_articles():
    """Initialize LightRAG and populate with Ghost articles."""
    WORKING_DIR = "./lightrag_ghost_data"
    
    if not os.path.exists(WORKING_DIR):
        os.mkdir(WORKING_DIR)

    rag = LightRAG(working_dir=WORKING_DIR)
    
    try:
        ghost_url = os.getenv("GHOST_APP_URL")
        ghost_api_key = os.getenv("GHOST_API_KEY")
        
        if not all([ghost_url, ghost_api_key]):
            logger.warning("Ghost credentials not configured, skipping article fetch")
            return rag
            
        articles = await fetch_ghost_articles(ghost_url, ghost_api_key)
        logger.info(f"Fetched {len(articles)} articles from Ghost")
        
        for article in articles:
            try:
                content = f"Title: {article.title}\nContent: {article.content}"
                rag.insert(content, metadata={
                    "url": article.url,
                    "title": article.title,
                    "id": article.id,
                    "source": "ghost"
                })
                logger.debug(f"Stored Ghost article: {article.title}")
                
            except Exception as e:
                logger.error(f"Error storing article {article.title}: {str(e)}")
                continue
                
        logger.info("Completed storing Ghost articles in LightRAG")
        
    except Exception as e:
        logger.error(f"Error fetching/storing Ghost articles: {str(e)}")
        
    return rag

def check_result_uniqueness(
    result: Dict, 
    rag: LightRAG,
    configuration: Configuration,
    conversation_history=None
) -> dict:
    """Check if a search result is unique against LightRAG knowledge store."""
    url = result.get('url', 'No URL')
    title = result.get('title', 'No title')
    similarity_threshold = configuration.similarity_threshold

    logger.info(f"=== Checking uniqueness for URL: {url} ===")
    logger.info(f"Using similarity threshold: {similarity_threshold}")
    logger.info(f"Title: {title}")
    logger.debug(f"Full result object: {result}")

    if not result.get('content'):
        logger.warning(f"Result missing content for URL: {url}")
        return {
            'is_unique': False,
            'similarity_score': 1.0,
            'similar_url': '',
            'reason': 'Missing content'
        }

    try:
        content = result.get('content', '')
        
        # Use hybrid search mode for better context understanding
        query_param = QueryParam(
            mode="hybrid",
            conversation_history=conversation_history,
            history_turns=3 if conversation_history else 0
        )
        
        # Query the RAG store with the content
        similar_results = rag.query(content, param=query_param)
        
        if similar_results:
            most_similar = similar_results[0]
            similarity_score = most_similar.get('score', 1.0)
            similar_url = most_similar.get('metadata', {}).get('url', 'No URL')
            
            logger.info(f"Similarity score: {similarity_score}")
            logger.info(f"Similar document URL: {similar_url}")
            
            if similarity_score <= similarity_threshold:
                return {
                    'is_unique': True,
                    'similarity_score': similarity_score,
                    'similar_url': similar_url,
                    'reason': f"Content is unique (score: {similarity_score})"
                }
            else:
                return {
                    'is_unique': False,
                    'similarity_score': similarity_score,
                    'similar_url': similar_url,
                    'reason': f"Content not unique (score: {similarity_score})"
                }
        else:
            return {
                'is_unique': True,
                'similarity_score': 0.0,
                'similar_url': '',
                'reason': 'No similar documents found'
            }

    except Exception as e:
        logger.error(f"Error checking uniqueness for {url}: {str(e)}", exc_info=True)
        return {
            'is_unique': False,
            'similarity_score': 1.0,
            'similar_url': '',
            'reason': f"Error: {str(e)}"
        }
