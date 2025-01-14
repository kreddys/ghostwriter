"""Tool for enriching unique results with additional search data."""

import os
import logging
import numpy as np
from typing import Dict, List, Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from pinecone import Pinecone

from ..state import State
from ..configuration import Configuration
from ..tools.combined_search import combined_search
from ..prompts import SEARCH_TERM_PROMPT
from ..llm import get_llm

logger = logging.getLogger(__name__)

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

async def check_relevance(
    original_result: Dict,
    additional_result: Dict,
    pinecone_client: Pinecone,
    configuration: Configuration
) -> bool:
    """Check if an additional result is relevant to the original result using Pinecone embeddings."""

    similarity_threshold = configuration.relevance_similarity_threshold

    try:
        original_url = original_result.get('url', 'No URL')
        additional_url = additional_result.get('url', 'No URL')
        
        logger.info(f"Checking relevance between:")
        logger.info(f"Original URL: {original_url}")
        logger.info(f"Additional URL: {additional_url}")

        original_text = f"{original_result.get('title', '')}. {original_result.get('content', '')}"
        additional_text = f"{additional_result.get('title', '')}. {additional_result.get('content', '')}"
        
        embeddings = pinecone_client.inference.embed(
            model="multilingual-e5-large",
            inputs=[original_text, additional_text],
            parameters={"input_type": "passage", "truncate": "END"}
        )
        
        vec1 = np.array(embeddings.data[0].values)
        vec2 = np.array(embeddings.data[1].values)
        
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
    model
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

async def process_direct_url(
    state: State,
    result: Dict,
    model,
    pinecone_client: Pinecone,
    config: RunnableConfig
) -> Dict:
    """Process a direct URL input for enrichment."""
    logger.info(f"Processing direct URL: {result.get('url')}")
    
    # Skip enrichment if Firecrawl was successful
    if result.get('scrape_status') == 'success':
        logger.info(f"Skipping enrichment for direct URL - Firecrawl successful")
        return {
            "original_result": result,
            "additional_results": []
        }
    
    try:
        search_term = await generate_search_term(result, model)
        
        additional_results = await combined_search(
            [search_term],
            config=config,
            state=state
        )
        
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
                    logger.info(f"Found relevant result for direct URL: '{additional_result.get('title')}'")
        
        return {
            "original_result": result,
            "additional_results": relevant_results
        }
        
    except Exception as e:
        logger.error(f"Error processing direct URL: {str(e)}")
        return {
            "original_result": result,
            "additional_results": []
        }

async def search_enricher(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> State:
    """Enrich unique results with additional search data."""
    logger.info("Starting search enrichment process")
    
    try:
        configuration = Configuration.from_runnable_config(config)
        pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        model = get_llm(configuration, temperature=0.7)
        
        enriched_results = {}
        
        # Handle direct URL case
        if state.is_direct_url:
            logger.info("Processing direct URL input")
            direct_result = state.search_results.get(state.direct_url.lower(), [])[0]
            
            enriched_result = await process_direct_url(
                state=state,
                result=direct_result,
                model=model,
                pinecone_client=pinecone_client,
                config=config
            )
            
            if enriched_result["additional_results"]:
                enriched_results[state.direct_url.lower()] = [enriched_result]
                logger.info(f"Successfully enriched direct URL with {len(enriched_result['additional_results'])} results")
            else:
                logger.warning("No relevant additional results found for direct URL")
                enriched_results[state.direct_url.lower()] = [{
                    "original_result": direct_result,
                    "additional_results": []
                }]
            
            state.enriched_results = enriched_results
            return state
        
        # Process regular search results
        for query, results in state.unique_results.items():
            if not isinstance(results, list):
                continue
                
            enriched_query_results = []
            for result in results:
                try:
                    # Skip enrichment if Firecrawl was successful
                    if result.get('scrape_status') == 'success':
                        logger.info(f"Skipping enrichment for '{result.get('title')}' - Firecrawl successful")
                        continue
                    
                    search_term = await generate_search_term(result, model)
                    
                    additional_results = await combined_search(
                        [search_term],
                        config=config,
                        state=state
                    )
                    
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
                                logger.info(f"Found relevant result: '{additional_result.get('title')}'")
                            else:
                                logger.info(f"Skipping irrelevant result: '{additional_result.get('title')}'")
                    
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
                        logger.warning(f"No relevant additional results found for: {result.get('title')}")
                    
                except Exception as e:
                    logger.error(f"Error enriching result: {str(e)}")
                    continue
            
            if enriched_query_results:
                enriched_results[query] = enriched_query_results
                logger.info(f"Stored {len(enriched_query_results)} enriched results for query '{query}'")
            else:
                logger.warning(f"No enriched results found for query: {query}")
        
        if not enriched_results:
            logger.warning("No relevant results found after enrichment")
            state.search_successful = False
            return state
        
        state.enriched_results = enriched_results
        logger.info("Enrichment complete")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in search enricher: {str(e)}")
        state.search_successful = False
        raise