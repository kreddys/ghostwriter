"""Google Search functionality."""
import os
from typing import Annotated, Any, Optional, Dict, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..configuration import Configuration
from ..state import State

async def google_search(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> Optional[List[Dict[str, Any]]]:
    """Search the web using Google Custom Search API."""
    try:
        configuration = Configuration.from_runnable_config(config)
        
        google_api_key = os.getenv("GOOGLE_API_KEY")
        google_cse_id = os.getenv("GOOGLE_CSE_ID")        

        if not google_api_key or not google_cse_id:
            raise ValueError("Google API key or CSE ID not found in environment variables")
        
        service = build("customsearch", "v1", developerKey=google_api_key)
        
        result = service.cse().list(
            q=query,
            cx=google_cse_id,
            num=configuration.max_search_results
        ).execute()
        
        processed_results = []
        
        if 'items' in result:
            for item in result['items']:
                processed_results.append({
                    "type": "text",
                    "title": item.get('title', 'N/A'),
                    "url": item.get('link', 'N/A'),
                    "content": item.get('snippet', 'N/A'),
                    "source": "google"
                })
        
        state.previous_searches.add(query)
        if query not in state.search_results:
            state.search_results[query] = []
        state.search_results[query].extend(processed_results)
        
        return processed_results
        
    except HttpError as e:
        raise ValueError(f"Google Search API error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error performing Google search: {str(e)}")