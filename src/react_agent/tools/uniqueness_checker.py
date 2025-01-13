"""Tool for checking uniqueness of search results using Pinecone."""
import logging
import os
from typing import Dict, Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_core.messages import SystemMessage
from langchain_pinecone import PineconeEmbeddings, PineconeVectorStore
from langchain.text_splitter import TokenTextSplitter
from pinecone import Pinecone
from supabase import create_client, Client
from ..state import State
from ..utils.ghost_api import fetch_ghost_articles
from ..configuration import Configuration
from ..prompts import RELEVANCY_CHECK_PROMPT 
from ..llm import get_llm
from ..utils.url_filter import filter_existing_urls

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

async def init_pinecone_with_ghost_articles():
    """Initialize Pinecone client and index, and populate with Ghost articles."""
    if not os.getenv("PINECONE_API_KEY"):
        raise ValueError("PINECONE_API_KEY environment variable not set")
    
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    # Get existing index
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    if index_name not in existing_indexes:
        raise ValueError(f"Index {index_name} does not exist in Pinecone")
    
    index = pc.Index(index_name)
    
    # Initialize vector store with embeddings
    embeddings = PineconeEmbeddings(model="multilingual-e5-large")
    vector_store = PineconeVectorStore(index=index, embedding=embeddings)
    
    # Fetch Ghost articles
    try:
        ghost_url = os.getenv("GHOST_APP_URL")
        ghost_api_key = os.getenv("GHOST_API_KEY")
        
        if not all([ghost_url, ghost_api_key]):
            logger.warning("Ghost credentials not configured, skipping article fetch")
            return vector_store
            
        articles = await fetch_ghost_articles(ghost_url, ghost_api_key)
        logger.info(f"Fetched {len(articles)} articles from Ghost")
        
        # Store articles in vector store
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

async def check_content_relevancy(content: dict, topic: str, model) -> bool:
    """Check if content is relevant to the specified topic using LLM."""
    try:
        messages = [
            SystemMessage(
                content=RELEVANCY_CHECK_PROMPT.format(
                    topic=topic,
                    title=content.get('title', 'N/A'),
                    content=content.get('content', 'N/A')
                )
            )
        ]
        
        response = await model.ainvoke(messages)
        is_relevant = response.content.lower().startswith('relevant')
        logger.info(f"Relevancy check for '{content.get('title')}': {is_relevant}")
        return is_relevant
        
    except Exception as e:
        logger.error(f"Error in relevancy check: {str(e)}")
        return False

def check_result_uniqueness(
    result: Dict, 
    vector_store: PineconeVectorStore,
    similarity_threshold: float = 0.85
) -> bool:
    """
    Check if a search result is unique against Pinecone database by splitting content 
    into chunks and checking each chunk for uniqueness.
    """
    logger.info(f"Checking uniqueness for result: {result.get('title', 'No title')}")
    logger.debug(f"Full result object: {result}")

    # Check if content exists
    if not result.get('content'):
        logger.warning("Result missing content")
        return False

    # Initialize text splitter for 500 token chunks
    text_splitter = TokenTextSplitter(
        chunk_size=500,
        chunk_overlap=50  # Some overlap to maintain context
    )
    
    try:
        # Split content into chunks
        content = result.get('content', '')
        content_chunks = text_splitter.split_text(content)
        logger.info(f"Split content into {len(content_chunks)} chunks")

        # Check each chunk for uniqueness
        for i, chunk in enumerate(content_chunks):
            logger.debug(f"Checking chunk {i+1}/{len(content_chunks)}")
            logger.debug(f"Chunk content: {chunk[:200]}...")

            similar_results = vector_store.similarity_search_with_score(
                chunk,
                k=1,
            )

            logger.info(f"Number of similar results found for chunk {i+1}: {len(similar_results)}")

            if similar_results:
                logger.info(f"Similar documents found for chunk {i+1}:")
                for doc, score in similar_results:
                    logger.info(f"Similarity score: {score}")
                    logger.info(f"Document content: {doc.page_content[:200]}...")
                    logger.info(f"Document metadata: {doc.metadata}")

                most_similar_doc, similarity_score = similar_results[0]
                
                # If any chunk is unique (score above threshold), the content is considered unique
                if similarity_score <= similarity_threshold:
                    logger.info(f"Found unique chunk {i+1} (score {similarity_score} <= threshold {similarity_threshold})")
                    return True
            else:
                # If no similar documents found for any chunk, it's unique
                logger.info(f"No similar documents found for chunk {i+1} - chunk is unique")
                return True

        # If we get here, no chunks were unique
        logger.info("No unique chunks found - content is not unique")
        return False

    except Exception as e:
        logger.error(f"Error during similarity search: {str(e)}", exc_info=True)
        logger.error(f"Vector store type: {type(vector_store)}")
        logger.error(f"Content length: {len(result.get('content', ''))}")
        return False

async def uniqueness_checker(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> State:
    """Filter and return unique search results using Pinecone and check topic relevancy."""
    logger.info("Starting uniqueness and relevancy check for search results")
    
    try:
        # Check for direct URL input
        if hasattr(state, 'is_direct_url') and state.is_direct_url:
            logger.info("Direct URL detected - skipping uniqueness and relevancy checks")
            
            # Pass through the direct URL result without checks
            if state.direct_url and state.direct_url.lower() in state.url_filtered_results:
                state.unique_results = {
                    state.direct_url.lower(): state.url_filtered_results[state.direct_url.lower()]
                }
                logger.info("Stored direct URL result without uniqueness/relevancy checks")
                return state
            else:
                logger.warning("Direct URL results not found in filtered results")
                state.unique_results = {}
                return state
        
        # Initialize configuration and LLM model for non-direct URL cases
        configuration = Configuration.from_runnable_config(config)
        use_url_filtering = configuration.use_url_filtering
        model = get_llm(configuration, temperature=0.3)

        # Initialize Pinecone and vector store
        vector_store = await init_pinecone_with_ghost_articles()
        
        unique_results = {}
        
        for query, results in state.url_filtered_results.items():
            if not isinstance(results, list):
                continue
                
            # First step: Filter existing URLs
            if use_url_filtering:
                logger.info("URL filtering enabled - filtering existing URLs")
                filtered_results = await filter_existing_urls(results)
            else:
                logger.info("URL filtering disabled - proceeding with all results")
                filtered_results = results
            
            # Second step: Check uniqueness and relevancy for remaining results
            source_unique_results = []
            for result in filtered_results:
                # Check uniqueness
                if check_result_uniqueness(result, vector_store):
                    # Then check relevancy
                    is_relevant = await check_content_relevancy(result, state.topic, model)
                    if is_relevant:
                        source_unique_results.append(result)
                        logger.info(f"Found unique and relevant result from {query}: {result.get('title', '')}")
                    else:
                        logger.info(f"Skipped irrelevant result from {query}: {result.get('title', '')}")
                else:
                    logger.info(f"Skipped duplicate result from {query}: {result.get('title', '')}")
            
            if source_unique_results:
                unique_results[query] = source_unique_results
        
        # Store unique results in state
        state.unique_results = unique_results
        logger.info(f"Stored {sum(len(results) for results in unique_results.values())} unique and relevant results in state")

        return state
        
    except Exception as e:
        logger.error(f"Error in uniqueness checker: {str(e)}")
        raise