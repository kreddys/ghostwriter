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
    """Search the web for current information using Tavily search engine."""
    # Normalize the query to prevent similar searches
    normalized_query = normalize_date_query(query)
    
    # Check if we already searched this or similar query
    if normalized_query in state.previous_searches:
        return state.search_results.get(normalized_query)
    
    # Perform search and store results
    configuration = Configuration.from_runnable_config(config)
    wrapped = TavilySearchResults(
        max_results=configuration.max_search_results,
        search_depth="advanced",
        include_answer=False,
        include_raw_content=True,
        include_images=True,
        topic="News",
        days=1,
    )
    
    result = await wrapped.ainvoke({"query": query})
    
    # Process and structure the results
    processed_results = []
    
    # Extract data from the artifact if available
    if isinstance(result, dict) and 'artifact' in result:
        artifact = result['artifact']
        
        # Add AI-generated answer if available
        if artifact.get('answer'):
            processed_results.append({
                'type': 'answer',
                'content': artifact['answer']
            })
        
        # Add images if available
        if artifact.get('images'):
            processed_results.append({
                'type': 'images',
                'content': artifact['images']
            })
        
        # Add text results
        if artifact.get('results'):
            for item in artifact['results']:
                processed_results.append({
                    'type': 'text',
                    'title': item.get('title', 'N/A'),
                    'url': item.get('url', 'N/A'),
                    'content': item.get('content', 'N/A')
                })
    else:
        # Handle direct results (non-artifact format)
        processed_results.extend([{
            'type': 'text',
            'title': item.get('title', 'N/A'),
            'url': item.get('url', 'N/A'),
            'content': item.get('content', 'N/A')
        } for item in (result if isinstance(result, list) else [])])
    
    # Store results for future reference
    state.previous_searches.add(normalized_query)
    state.search_results[normalized_query] = processed_results
    
    return processed_results

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
