"""Combined search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from ..utils.google_search import google_search
from ..utils.tavily_search import tavily_search
from ..state import State

logger = logging.getLogger(__name__)

async def combined_search(
    query: str, *, 
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Combine results from both Google and Tavily search."""
    logger.info(f"Starting combined search for query: {query}")
    
    # Get results from both sources
    google_results = await google_search(query, config=config, state=state)
    tavily_results = await tavily_search(query, config=config, state=state)
    
    # Filter function to check if result is about Amaravati
    def is_relevant_to_amaravati(result):
        text = (
            (result.get('title', '') + ' ' + result.get('content', '')).lower()
        )
        return 'amaravati' in text and 'andhra pradesh' in text
    
    # Filter and combine results
    combined_results = []
    if google_results:
        filtered_google = [r for r in google_results if is_relevant_to_amaravati(r)]
        combined_results.extend(filtered_google)
    # if tavily_results:
    #     filtered_tavily = [r for r in tavily_results if is_relevant_to_amaravati(r)]
    #     combined_results.extend(filtered_tavily)
    
    # Sort by date if available
    combined_results.sort(
        key=lambda x: x.get('published_date', ''), 
        reverse=True
    )
    
    logger.info(f"Combined search completed with {len(combined_results)} relevant results")
    return combined_results