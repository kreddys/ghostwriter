"""Tavily Search functionality."""
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from tavily import TavilyClient, InvalidAPIKeyError, MissingAPIKeyError, UsageLimitExceededError

from ..configuration import Configuration
from ..state import State

async def tavily_search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg], 
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Search the web using Tavily search engine."""
    try:
        configuration = Configuration.from_runnable_config(config)
        tavily_client = TavilyClient()
        
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=configuration.max_search_results,
            include_answer=True,
            include_raw_content=True,
            include_images=True,
            topic="general",
            days=1
        )
        
        processed_results = []
        
        if response.get("answer"):
            processed_results.append({
                "type": "answer",
                "content": response["answer"],
                "source": "tavily"
            })
        
        if response.get("images"):
            processed_results.append({
                "type": "images",
                "content": response["images"],
                "source": "tavily"
            })
        
        if response.get("results"):
            for item in response["results"]:
                processed_results.append({
                    "type": "text",
                    "title": item.get("title", "N/A"),
                    "url": item.get("url", "N/A"),
                    "content": item.get("content", "N/A"),
                    "score": item.get("score", 0.0),
                    "source": "tavily"
                })
        
        state.previous_searches.add(query)
        state.search_results[query] = processed_results
        
        return processed_results
        
    except MissingAPIKeyError:
        raise ValueError("Tavily API key is missing. Please set the TAVILY_API_KEY environment variable.")
    except InvalidAPIKeyError:
        raise ValueError("Invalid Tavily API key. Please check your API key.")
    except UsageLimitExceededError:
        raise ValueError("Tavily API usage limit exceeded. Please check your plan limits.")
    except Exception as e:
        raise ValueError(f"Error performing Tavily search: {str(e)}")