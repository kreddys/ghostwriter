"""Combined search functionality."""
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from ..state import State
from .google_search import google_search
from .tavily_search import tavily_search

async def combined_search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Perform both Tavily and Google searches and combine results."""
    try:
        tavily_results = await tavily_search(query, config=config, state=state)
        google_results = await google_search(query, config=config, state=state)
        
        combined_results = []
        
        if tavily_results:
            combined_results.extend(tavily_results)
                
        if google_results:
            combined_results.extend(google_results)
            
        return combined_results
        
    except Exception as e:
        raise ValueError(f"Error performing combined search: {str(e)}")