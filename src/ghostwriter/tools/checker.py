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
from ..utils.ghost.api import fetch_ghost_articles
from ..configuration import Configuration
from ..prompts import RELEVANCY_CHECK_PROMPT 
from ..llm import get_llm
from ..utils.unique.url_filter_supabase import filter_existing_urls

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

async def check_content_relevancy(content: dict, topic: str, model) -> bool:
    """Check if content is relevant to the specified topic using LLM."""
    url = content.get('url', 'No URL')
    title = content.get('title', 'No title')
    
    logger.info(f"Checking relevancy for URL: {url}")
    logger.info(f"Title: {title}")
    logger.info(f"Topic: {topic}")
    
    try:
        messages = [
            SystemMessage(
                content=RELEVANCY_CHECK_PROMPT.format(
                    topic=topic,
                    title=title,
                    content=content.get('content', 'N/A')
                )
            )
        ]
        
        response = await model.ainvoke(messages)
        is_relevant = response.content.lower().startswith('relevant')
        
        logger.info(f"Relevancy check result for {url}: {'RELEVANT' if is_relevant else 'NOT RELEVANT'}")
        return is_relevant
        
    except Exception as e:
        logger.error(f"Error in relevancy check for {url}: {str(e)}")
        return False

def check_result_uniqueness(
    result: Dict, 
    vector_store: PineconeVectorStore,
    configuration: Configuration
) -> bool:
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
        return False

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
                logger.info(f"Chunk {i+1} similarity score: {similarity_score}")
                logger.info(f"Similar document URL: {most_similar_doc.metadata.get('url', 'No URL')}")
                
                if similarity_score <= similarity_threshold:
                    logger.info(f"Found unique chunk for {url} (score: {similarity_score})")
                    return True
            else:
                logger.info(f"No similar documents found for chunk {i+1} of {url}")
                return True

        logger.info(f"Content not unique for {url}")
        return False

    except Exception as e:
        logger.error(f"Error checking uniqueness for {url}: {str(e)}", exc_info=True)
        return False

async def uniqueness_checker(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> State:
    """Filter and return unique search results using Pinecone and check topic relevancy."""
    logger.info("=== Starting uniqueness and relevancy check for search results ===")
    logger.info(f"Initial number of URLs to process: {sum(len(results) if isinstance(results, list) else 0 for results in state.url_filtered_results.values())}")
    
    try:
        if hasattr(state, 'is_direct_url') and state.is_direct_url:
            logger.info("Direct URL detected - skipping uniqueness and relevancy checks")
            if state.direct_url and state.direct_url.lower() in state.url_filtered_results:
                state.unique_results = {
                    state.direct_url.lower(): state.url_filtered_results[state.direct_url.lower()]
                }
                logger.info(f"Stored direct URL result: {state.direct_url}")
                return state
            else:
                logger.warning("Direct URL results not found in filtered results")
                state.unique_results = {}
                return state
        
        configuration = Configuration.from_runnable_config(config)
        use_url_filtering = configuration.use_url_filtering
        model = get_llm(configuration, temperature=0.3)
        vector_store = await init_pinecone_with_ghost_articles()
        
        unique_results = {}
        total_processed = 0
        total_unique = 0
        total_relevant = 0
        
        for query, results in state.url_filtered_results.items():
            if not isinstance(results, list):
                continue
                
            logger.info(f"\nProcessing query: {query}")
            logger.info(f"Number of results to process: {len(results)}")
            
            if use_url_filtering:
                filtered_results = await filter_existing_urls(results)
                logger.info(f"URLs after filtering: {len(filtered_results)} (filtered out {len(results) - len(filtered_results)})")
            else:
                filtered_results = results
                logger.info("URL filtering disabled - processing all results")
            
            source_unique_results = []
            
            for result in filtered_results:
                total_processed += 1
                url = result.get('url', 'No URL')
                
                # Check uniqueness
                is_unique = check_result_uniqueness(result, vector_store, configuration)
                if is_unique:
                    total_unique += 1
                    # Check relevancy
                    is_relevant = await check_content_relevancy(result, state.topic, model)
                    if is_relevant:
                        total_relevant += 1
                        source_unique_results.append(result)
                        logger.info(f"✓ Accepted URL (unique and relevant): {url}")
                    else:
                        logger.info(f"✗ Rejected URL (not relevant): {url}")
                else:
                    logger.info(f"✗ Rejected URL (not unique): {url}")
            
            if source_unique_results:
                unique_results[query] = source_unique_results
        
        state.unique_results = unique_results
        
        logger.info("\n=== Uniqueness Checker Summary ===")
        logger.info(f"Total URLs processed: {total_processed}")
        logger.info(f"Unique URLs found: {total_unique}")
        logger.info(f"Relevant URLs found: {total_relevant}")
        logger.info(f"Final unique and relevant URLs: {sum(len(results) for results in unique_results.values())}")

        return state
        
    except Exception as e:
        logger.error(f"Error in uniqueness checker: {str(e)}")
        raise