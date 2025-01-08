"""Combined search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from .google_search import google_search
from .tavily_search import tavily_search
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
    
    # Combine results
    combined_results = []
    if google_results:
        combined_results.extend(google_results)
    if tavily_results:
        combined_results.extend(tavily_results)
    
    logger.info(f"Combined search completed with {len(combined_results)} total results")
    return combined_results