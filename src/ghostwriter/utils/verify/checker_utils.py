"""Utility functions for content checking and chunking."""
import logging
from typing import List
from langchain.text_splitter import TokenTextSplitter

logger = logging.getLogger(__name__)

def split_content_into_chunks(content: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """Split content into smaller chunks for processing."""
    if not content:
        return []
        
    try:
        text_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        chunks = text_splitter.split_text(content)
        logger.info(f"Split content into {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error splitting content: {str(e)}")
        return [content]  # Return original content as single chunk on error

def truncate_content(content: str, max_length: int = 100000) -> str:
    """Truncate content if it exceeds maximum length."""
    if len(content) > max_length:
        logger.warning(f"Content length ({len(content)} chars) exceeds limit, truncating...")
        return content[:max_length]
    return content