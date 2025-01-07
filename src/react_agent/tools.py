"""This module provides example tools for web scraping and search functionality."""
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from tavily import TavilyClient, InvalidAPIKeyError, MissingAPIKeyError, UsageLimitExceededError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .configuration import Configuration
from .state import State

async def google_search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Search the web using Google Custom Search API."""
    try:
        configuration = Configuration.from_runnable_config(config)

        # Get API keys from environment variables
        google_api_key = os.getenv("GOOGLE_API_KEY")
        google_cse_id = os.getenv("GOOGLE_CSE_ID")        

        if not google_api_key or not google_cse_id:
            raise ValueError("Google API key or CSE ID not found in environment variables")
        
        # Initialize Google Custom Search API client
        service = build("customsearch", "v1", developerKey=configuration.google_api_key)
        
        # Perform the search
        result = service.cse().list(
            q=query,
            cx=configuration.google_cse_id,  # Custom Search Engine ID
            num=configuration.max_search_results
        ).execute()
        
        processed_results = []
        
        # Process search results
        if 'items' in result:
            for item in result['items']:
                processed_results.append({
                    "type": "text",
                    "title": item.get('title', 'N/A'),
                    "url": item.get('link', 'N/A'),
                    "content": item.get('snippet', 'N/A'),
                    "source": "google"
                })
        
        # Store results in state
        state.previous_searches.add(query)
        if query not in state.search_results:
            state.search_results[query] = []
        state.search_results[query].extend(processed_results)
        
        return processed_results
        
    except HttpError as e:
        raise ValueError(f"Google Search API error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error performing Google search: {str(e)}")

async def search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg], 
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Search the web for current information using Tavily search engine."""
    try:
        # Initialize Tavily client
        configuration = Configuration.from_runnable_config(config)
        tavily_client = TavilyClient()  # API key will be read from environment variable
        
        # Perform search with specified parameters
        response = tavily_client.search(
            query=query,
            search_depth="advanced",  # Using advanced search for better results
            max_results=configuration.max_search_results,
            include_answer=True,
            include_raw_content=True,
            include_images=True,
            topic="general",
            days=1
        )
        
        # Process and structure the results
        processed_results = []
        
        # Add AI-generated answer if available
        if response.get("answer"):
            processed_results.append({
                "type": "answer",
                "content": response["answer"]
            })
        
        # Add images if available
        if response.get("images"):
            processed_results.append({
                "type": "images",
                "content": response["images"]
            })
        
        # Add text results
        if response.get("results"):
            for item in response["results"]:
                processed_results.append({
                    "type": "text",
                    "title": item.get("title", "N/A"),
                    "url": item.get("url", "N/A"),
                    "content": item.get("content", "N/A"),
                    "score": item.get("score", 0.0)
                })
        
        # Store results in state
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

async def combined_search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Perform both Tavily and Google searches and combine results."""
    try:
        # Get results from both search engines
        tavily_results = await search(query, config=config, state=state)
        google_results = await google_search(query, config=config, state=state)
        
        combined_results = []
        
        # Add Tavily results if available
        if tavily_results:
            for result in tavily_results:
                result['source'] = 'tavily'
                combined_results.append(result)
                
        # Add Google results if available
        if google_results:
            combined_results.extend(google_results)
            
        return combined_results
        
    except Exception as e:
        raise ValueError(f"Error performing combined search: {str(e)}")