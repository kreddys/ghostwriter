"""Article Writer Agent functionality."""

import os
import json
import logging
from typing import Dict, List
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ..prompts import ARTICLE_WRITER_PROMPT
from ..state import State
from ..configuration import Configuration
from ghostwriter.utils.ghost.api import fetch_ghost_tags
from ..llm import get_llm 

logger = logging.getLogger(__name__)

async def article_writer_agent(
    state: State,
    config: RunnableConfig,
) -> State:
    """
    Agent that processes search results and generates articles in Ghost-compatible format.

    Args:
        state: Current state containing search results and messages
        config: Configuration for the agent

    Returns:
        Updated state containing generated articles
    """
    logger.info("Starting Article Writer Agent")

    configuration = Configuration.from_runnable_config(config)
    logger.info(f"Using model: {configuration.model}")

    # Fetch Ghost CMS tags
    app_url = os.getenv("GHOST_APP_URL")
    ghost_api_key = os.getenv("GHOST_API_KEY")
    
    if not app_url:
        raise ValueError("GHOST_APP_URL environment variable not set")
    if not ghost_api_key:
        raise ValueError("GHOST_API_KEY environment variable not set")
    
    ghost_tags = await fetch_ghost_tags(app_url, ghost_api_key)
    tag_names = [tag.name for tag in ghost_tags]

    model = get_llm(configuration, temperature=0.8, max_tokens=4096)    

    generated_articles = []
    
    # Determine which results to use based on configuration
    if configuration.use_search_enricher:
        logger.info("Using enriched search results for article generation")
        results_to_process = state.enriched_results
        for results in results_to_process.values():
            if isinstance(results, list):
                for enriched_result in results:
                    # Prepare combined content from original and additional results
                    original_result = enriched_result["original_result"]
                    additional_results = enriched_result["additional_results"]
                    
                    combined_content = f"""
                    Original Article:
                    Title: {original_result.get('title', 'N/A')}
                    URL: {original_result.get('url', 'N/A')}
                    Content: {original_result.get('content', 'N/A')}
                    
                    Additional Information:
                    {format_additional_results(additional_results)}
                    """
                    
                    messages = [
                        SystemMessage(
                            content=ARTICLE_WRITER_PROMPT.format(
                                tag_names=tag_names,
                                web_search_results=combined_content
                            )
                        )
                    ]
                    
                    response = await model.ainvoke(messages)
                    generated_articles.append(AIMessage(content=response.content))
    else:
        logger.info("Using unique search results for article generation")
        results_to_process = state.unique_results
        for results in results_to_process.values():
            if isinstance(results, list):
                for result in results:
                    content = f"""
                    Title: {result.get('title', 'N/A')}
                    URL: {result.get('url', 'N/A')}
                    Content: {result.get('content', 'N/A')}
                    """
                    
                    messages = [
                        SystemMessage(
                            content=ARTICLE_WRITER_PROMPT.format(
                                tag_names=tag_names,
                                web_search_results=content
                            )
                        )
                    ]
                    
                    response = await model.ainvoke(messages)
                    generated_articles.append(AIMessage(content=response.content))
    
    # Store all generated articles
    state.articles["messages"] = generated_articles
    logger.info(f"Generated {len(generated_articles)} articles")
    
    return state

def format_additional_results(results: List[Dict]) -> str:
    """Format additional search results for article generation."""
    if not results:
        return "No additional information found."
        
    formatted_results = []
    for result in results:
        formatted_results.append(
            f"Title: {result.get('title', 'N/A')}\n"
            f"URL: {result.get('url', 'N/A')}\n"
            f"Content: {result.get('content', 'N/A')}\n"
        )
    
    return "\n\n".join(formatted_results)