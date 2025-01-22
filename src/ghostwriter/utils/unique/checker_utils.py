"""Utility functions for uniqueness checking."""
import logging
import os
from typing import Dict
from langchain_pinecone import PineconeEmbeddings, PineconeVectorStore
from langchain.text_splitter import TokenTextSplitter
from pinecone import Pinecone
from ghostwriter.configuration import Configuration
from ghostwriter.utils.ghost.api import fetch_ghost_articles

logger = logging.getLogger(__name__)

async def init_pinecone_with_ghost_articles():
    """Initialize Pinecone client and index, and populate with Ghost articles."""
    if not os.getenv("PINECONE_API_KEY"):
        raise ValueError("PINECONE_API_KEY environment variable not set")
    
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    logger.info(f"Initializing Pinecone with index: {index_name}")
    
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    if index_name not in existing_indexes:
        raise ValueError(f"Index {index_name} does not exist in Pinecone")
    
    index = pc.Index(index_name)
    embeddings = PineconeEmbeddings(model="multilingual-e5-large")
    vector_store = PineconeVectorStore(index=index, embedding=embeddings)
    
    try:
        ghost_url = os.getenv("GHOST_APP_URL")
        ghost_api_key = os.getenv("GHOST_API_KEY")
        
        if not all([ghost_url, ghost_api_key]):
            logger.warning("Ghost credentials not configured, skipping article fetch")
            return vector_store
            
        articles = await fetch_ghost_articles(ghost_url, ghost_api_key)
        logger.info(f"Fetched {len(articles)} articles from Ghost")
        
        for article in articles:
            try:
                content = f"Title: {article.title}\nContent: {article.content}"
                metadata = {
                    "url": article.url,
                    "title": article.title,
                    "id": article.id,
                    "source": "ghost"
                }
                
                vector_store.add_texts(
                    texts=[content],
                    metadatas=[metadata],
                    ids=[article.id]
                )
                logger.debug(f"Stored Ghost article: {article.title}")
                
            except Exception as e:
                logger.error(f"Error storing article {article.title}: {str(e)}")
                continue
                
        logger.info("Completed storing Ghost articles in Pinecone")
        
    except Exception as e:
        logger.error(f"Error fetching/storing Ghost articles: {str(e)}")
        
    return vector_store

def check_result_uniqueness(
    result: Dict, 
    vector_store: PineconeVectorStore,
    configuration: Configuration
) -> dict:
    """Check if a search result is unique against Pinecone database."""
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

    text_splitter = TokenTextSplitter(chunk_size=500, chunk_overlap=50)
    
    try:
        content = result.get('content', '')
        content_chunks = text_splitter.split_text(content)
        logger.info(f"Split content into {len(content_chunks)} chunks for {url}")

        for i, chunk in enumerate(content_chunks):
            logger.debug(f"Checking chunk {i+1}/{len(content_chunks)} for {url}")
            
            similar_results = vector_store.similarity_search_with_score(chunk, k=1)
            
            if similar_results:
                most_similar_doc, similarity_score = similar_results[0]
                similar_url = most_similar_doc.metadata.get('url', 'No URL')
                logger.info(f"Chunk {i+1} similarity score: {similarity_score}")
                logger.info(f"Similar document URL: {similar_url}")
                
                if similarity_score <= similarity_threshold:
                    logger.info(f"Found unique chunk for {url} (score: {similarity_score})")
                    return {
                        'is_unique': True,
                        'similarity_score': similarity_score,
                        'similar_url': similar_url,
                        'reason': f"Unique chunk found (score: {similarity_score})"
                    }
            else:
                logger.info(f"No similar documents found for chunk {i+1} of {url}")
                return {
                    'is_unique': True,
                    'similarity_score': 0.0,
                    'similar_url': '',
                    'reason': 'No similar documents found'
                }

        logger.info(f"Content not unique for {url}")
        return {
            'is_unique': False,
            'similarity_score': similarity_score,
            'similar_url': similar_url,
            'reason': f"Content not unique (score: {similarity_score})"
        }

    except Exception as e:
        logger.error(f"Error checking uniqueness for {url}: {str(e)}", exc_info=True)
        return {
            'is_unique': False,
            'similarity_score': 1.0,
            'similar_url': '',
            'reason': f"Error: {str(e)}"
        }
