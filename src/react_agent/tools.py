"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""

from typing import Any, Callable, List, Optional, cast

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from typing_extensions import Annotated

from react_agent.configuration import Configuration
from react_agent.state import State


async def search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg], 
    state: State
) -> Optional[list[dict[str, Any]]]:
    # Normalize the query to prevent similar searches
    normalized_query = normalize_date_query(query)
    
    # Check if we already searched this or similar query
    if normalized_query in state.previous_searches:
        return state.search_results.get(normalized_query)
    
    # Perform search and store results
    configuration = Configuration.from_runnable_config(config)
    wrapped = TavilySearchResults(max_results=configuration.max_search_results)
    result = await wrapped.ainvoke({"query": query})
    
    # Store results for future reference
    state.previous_searches.add(normalized_query)
    state.search_results[normalized_query] = result
    
    return result

def normalize_date_query(query: str) -> str:
    """Normalize date-related terms in queries to prevent duplicates"""
    date_terms = {
        "last 1 day": "recent",
        "last 24 hours": "recent",
        "today": "recent",
        "latest": "recent"
    }
    normalized = query.lower()
    for term, replacement in date_terms.items():
        normalized = normalized.replace(term, replacement)
    return normalized


TOOLS: List[Callable[..., Any]] = [search]
