"""Tavily Search functionality."""
import logging
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from tavily import TavilyClient, InvalidAPIKeyError, MissingAPIKeyError, UsageLimitExceededError

from ..configuration import Configuration
from ..state import State

logger = logging.getLogger(__name__)

async def tavily_search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg], 
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Search the web using Tavily search engine."""
    logger.info(f"Starting Tavily search for query: {query}")
    
    try:
        configuration = Configuration.from_runnable_config(config)
        logger.debug("Initializing Tavily client")
        tavily_client = TavilyClient()
        
        logger.info(f"Executing Tavily search with max results: {configuration.max_search_results}")
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=configuration.max_search_results,
            include_answer=True,
            include_raw_content=True,
            include_images=True,
            topic="news",
            days=configuration.search_days
        )
        
        logger.debug(f"Raw Tavily API response: {response}")
        processed_results = []
        
        # Process results to match Google format
        if response.get("results"):
            logger.info(f"Found {len(response['results'])} results from Tavily search")
            for item in response["results"]:
                processed_results.append({
                    "type": "text",
                    "title": item.get("title", "N/A"),
                    "url": item.get("url", "N/A"),
                    "content": item.get("content", "N/A"),
                    "source": "tavily"
                })
        
        state.previous_searches.add(query)
        state.search_results[query] = processed_results
        
        logger.info(f"Successfully processed {len(processed_results)} Tavily search results")
        return processed_results
        
    except MissingAPIKeyError:
        logger.error("Tavily API key is missing", exc_info=True)
        raise ValueError("Tavily API key is missing. Please set the TAVILY_API_KEY environment variable.")
    except InvalidAPIKeyError:
        logger.error("Invalid Tavily API key", exc_info=True)
        raise ValueError("Invalid Tavily API key. Please check your API key.")
    except UsageLimitExceededError:
        logger.error("Tavily API usage limit exceeded", exc_info=True)
        raise ValueError("Tavily API usage limit exceeded. Please check your plan limits.")
    except Exception as e:
        logger.error(f"Unexpected error in Tavily search: {str(e)}", exc_info=True)
        raise ValueError(f"Error performing Tavily search: {str(e)}")