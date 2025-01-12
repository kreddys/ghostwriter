"""Tool for enriching unique results with additional search data."""

import os
import logging
import numpy as np
from typing import Dict, List, Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pinecone import Pinecone

from ..state import State
from ..configuration import Configuration
from ..tools.combined_search import combined_search

logger = logging.getLogger(__name__)

SEARCH_TERM_PROMPT = """
Given the title and content of an article, generate a search query that will help find additional relevant information.
Focus on the main topic and key concepts. The query should be concise but comprehensive enough to find related content.

Article Title: {title}
Article Content: {content}

Generate a search query that will help find additional relevant information about this topic.
Return only the search query, nothing else.
"""

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

async def check_relevance(
    original_result: Dict,
    additional_result: Dict,
    pinecone_client: Pinecone,
    similarity_threshold: float = 0.75
) -> bool:
    """Check if an additional result is relevant to the original result using Pinecone embeddings."""
    try:
        # Prepare texts for embedding
        original_text = f"{original_result.get('title', '')}. {original_result.get('content', '')}"
        additional_text = f"{additional_result.get('title', '')}. {additional_result.get('snippet', '')}"
        
        # Generate embeddings
        embeddings = pinecone_client.inference.embed(
            model="multilingual-e5-large",
            inputs=[original_text, additional_text],
            parameters={"input_type": "passage", "truncate": "END"}
        )
        
        # Extract embedding vectors
        vec1 = np.array(embeddings.data[0].values)
        vec2 = np.array(embeddings.data[1].values)
        
        # Calculate similarity
        similarity = cosine_similarity(vec1, vec2)
        is_relevant = similarity >= similarity_threshold
        
        logger.info(
            f"Relevance score between '{original_result.get('title')}' and "
            f"'{additional_result.get('title')}': {similarity:.4f}"
        )
        
        return is_relevant
        
    except Exception as e:
        logger.error(f"Error checking relevance: {str(e)}")
        return False

async def generate_search_term(
    result: Dict,
    model: ChatOllama | ChatOpenAI
) -> str:
    """Generate a search term from a result's title and content."""
    try:
        prompt = SEARCH_TERM_PROMPT.format(
            title=result.get('title', ''),
            content=result.get('content', '')[:500]
        )
        
        response = await model.ainvoke([{"role": "user", "content": prompt}])
        search_term = response.content.strip()
        
        logger.info(f"Generated search term: {search_term} for title: {result.get('title')}")
        return search_term
        
    except Exception as e:
        logger.error(f"Error generating search term: {str(e)}")
        return result.get('title', '')

async def search_enricher(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> State:
    """Enrich unique results with additional search data."""
    logger.info("Starting search enrichment process")
    
    try:
        configuration = Configuration.from_runnable_config(config)
        
        # Initialize Pinecone client
        pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        # Initialize the model for search term generation
        if configuration.model.startswith("deepseek/"):
            model = ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
                openai_api_base="https://api.deepseek.com/v1",
                temperature=0.7
            )
        else:
            model = ChatOllama(
                model=configuration.model.split("/")[1],
                base_url="http://host.docker.internal:11434",
                temperature=0.7
            )
        
        enriched_results = {}
        
        # Process each unique result
        for query, results in state.unique_results.items():
            if not isinstance(results, list):
                continue
                
            enriched_query_results = []
            for result in results:
                try:
                    # Generate search term from result
                    search_term = await generate_search_term(result, model)
                    
                    # Perform combined search with generated term
                    additional_results = await combined_search(
                        [search_term],
                        config=config,
                        state=state
                    )
                    
                    # Filter relevant results
                    relevant_results = []
                    if additional_results:
                        for additional_result in additional_results:
                            is_relevant = await check_relevance(
                                original_result=result,
                                additional_result=additional_result,
                                pinecone_client=pinecone_client
                            )
                            
                            if is_relevant:
                                relevant_results.append(additional_result)
                                logger.info(
                                    f"Found relevant result: "
                                    f"'{additional_result.get('title')}'"
                                )
                            else:
                                logger.info(
                                    f"Skipping irrelevant result: "
                                    f"'{additional_result.get('title')}'"
                                )
                    
                    # Only include results with relevant additional content
                    if relevant_results:
                        enriched_result = {
                            "original_result": result,
                            "additional_results": relevant_results
                        }
                        enriched_query_results.append(enriched_result)
                        logger.info(
                            f"Added enriched result for '{result.get('title')}' "
                            f"with {len(relevant_results)} relevant results"
                        )
                    else:
                        logger.warning(
                            f"No relevant additional results found for: "
                            f"{result.get('title')}"
                        )
                    
                except Exception as e:
                    logger.error(f"Error enriching result: {str(e)}")
                    continue
            
            if enriched_query_results:
                enriched_results[query] = enriched_query_results
                logger.info(
                    f"Stored {len(enriched_query_results)} enriched results "
                    f"for query '{query}'"
                )
            else:
                logger.warning(f"No enriched results found for query: {query}")
        
        if not enriched_results:
            logger.warning("No relevant results found after enrichment")
            state.search_successful = False
            return state
        
        # Store enriched results in state
        state.enriched_results = enriched_results
        logger.info("Enrichment complete")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in search enricher: {str(e)}")
        state.search_successful = False
        raise