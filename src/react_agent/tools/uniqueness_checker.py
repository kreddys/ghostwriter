"""Tool for checking uniqueness of search results using Pinecone."""
import logging
import os
from typing import Dict, Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_pinecone import PineconeEmbeddings, PineconeVectorStore
from pinecone import Pinecone
from ..state import State

logger = logging.getLogger(__name__)

def init_pinecone():
    """Initialize Pinecone client and index."""
    if not os.getenv("PINECONE_API_KEY"):
        raise ValueError("PINECONE_API_KEY environment variable not set")
    
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    # Get existing index
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    if index_name not in existing_indexes:
        raise ValueError(f"Index {index_name} does not exist in Pinecone")
    
    return pc.Index(index_name)

def check_result_uniqueness(
    result: Dict, 
    vector_store: PineconeVectorStore,
    similarity_threshold: float = 0.85
) -> bool:
    """Check if a search result is unique against Pinecone database."""
    # Skip if no title or content
    if not result.get('title') and not result.get('content'):
        logger.warning("Result missing both title and content")
        return False
        
    query = f"Title: {result.get('title', '')}\nContent: {result.get('content', '')}"
    
    try:
        # Search for similar documents
        similar_results = vector_store.similarity_search_with_score(
            query,
            k=1
        )
        
        if not similar_results:
            return True
            
        _, score = similar_results[0]
        return score <= similarity_threshold
        
    except Exception as e:
        logger.error(f"Error during similarity search: {str(e)}")
        return False

async def uniqueness_checker(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> State:
    """Filter and return unique search results using Pinecone."""
    logger.info("Starting uniqueness check for search results using Pinecone")
    
    try:
        # Initialize Pinecone and vector store
        index = init_pinecone()
        embeddings = PineconeEmbeddings(model="multilingual-e5-large")
        vector_store = PineconeVectorStore(index=index, embedding=embeddings)
        
        unique_results = {}
        
        for query, results in state.url_filtered_results.items():
            if not isinstance(results, list):
                continue
                
            source_unique_results = []
            for result in results:
                if check_result_uniqueness(result, vector_store):
                    source_unique_results.append(result)
                    logger.info(f"Found unique result from {query}: {result.get('title', '')}")
                else:
                    logger.info(f"Skipped duplicate result from {query}: {result.get('title', '')}")
            
            if source_unique_results:
                unique_results[query] = source_unique_results
        
        # Store unique results in state
        state.unique_results = unique_results
        logger.info(f"Stored unique results in state")

        return state
        
    except Exception as e:
        logger.error(f"Error in uniqueness checker: {str(e)}")
        raise