"""Tool for enriching unique results with additional search data."""

import os
import logging
from typing import Dict, List, Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

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

async def generate_search_term(
    result: Dict,
    model: ChatOllama | ChatOpenAI
) -> str:
    """Generate a search term from a result's title and content."""
    try:
        # Prepare the prompt with the result data
        prompt = SEARCH_TERM_PROMPT.format(
            title=result.get('title', ''),
            content=result.get('content', '')[:500]  # Limit content length
        )
        
        # Get search term from model
        response = await model.ainvoke([{"role": "user", "content": prompt}])
        search_term = response.content.strip()
        
        logger.info(f"Generated search term: {search_term} for title: {result.get('title')}")
        return search_term
        
    except Exception as e:
        logger.error(f"Error generating search term: {str(e)}")
        return result.get('title', '')  # Fallback to using the title as search term

async def search_enricher(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> State:
    """Enrich unique results with additional search data."""
    logger.info("Starting search enrichment process")
    
    try:
        configuration = Configuration.from_runnable_config(config)
        
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
                    
                    # Combine original result with additional search results
                    enriched_result = {
                        "original_result": result,
                        "additional_results": additional_results or []
                    }
                    
                    enriched_query_results.append(enriched_result)
                    logger.info(f"Enriched result for: {result.get('title')}")
                    
                except Exception as e:
                    logger.error(f"Error enriching result: {str(e)}")
                    # Include original result without enrichment
                    enriched_query_results.append({
                        "original_result": result,
                        "additional_results": []
                    })
            
            if enriched_query_results:
                enriched_results[query] = enriched_query_results
        
        # Store enriched results in state
        state.enriched_results = enriched_results
        logger.info(f"Stored enriched results in state")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in search enricher: {str(e)}")
        raise