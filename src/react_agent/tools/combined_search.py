"""Combined search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from ..state import State
from .google_search import google_search
from .tavily_search import tavily_search

logger = logging.getLogger(__name__)

async def combined_search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Perform both Tavily and Google searches and combine results."""
    logger.info(f"Starting combined search for query: {query}")
    
    try:
        logger.debug("Executing Tavily search")
        tavily_results = await tavily_search(query, config=config, state=state)
        logger.info(f"Tavily search returned {len(tavily_results) if tavily_results else 0} results")
        
        logger.debug("Executing Google search")
        google_results = await google_search(query, config=config, state=state)
        logger.info(f"Google search returned {len(google_results) if google_results else 0} results")
        
        combined_results = []
        
        if tavily_results:
            combined_results.extend(tavily_results)
                
        if google_results:
            combined_results.extend(google_results)
            
        logger.info(f"Combined search completed with {len(combined_results)} total results")
        return combined_results
        
    except Exception as e:
        logger.error(f"Error in combined search: {str(e)}", exc_info=True)
        raise ValueError(f"Error performing combined search: {str(e)}")