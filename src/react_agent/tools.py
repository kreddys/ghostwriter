"""This module provides example tools for web scraping and search functionality."""
import logging
from .tools.google_search import google_search
from .tools.tavily_search import tavily_search
from .tools.combined_search import combined_search

logger = logging.getLogger(__name__)

def logged_google_search(*args, **kwargs):
    logger.info(f"Executing Google search with args: {args}, kwargs: {kwargs}")
    results = google_search(*args, **kwargs)
    # Google results are already in the correct format with 'source': 'google'
    logger.info(f"Google search results: {results}")
    return results

def logged_tavily_search(*args, **kwargs):
    logger.info(f"Executing Tavily search with args: {args}, kwargs: {kwargs}")
    results = tavily_search(*args, **kwargs)
    # Transform Tavily results to match Google format
    formatted_results = [{
        'type': 'text',
        'title': result.get('title', ''),
        'url': result.get('url', ''),
        'content': result.get('content', ''),
        'source': 'tavily'
    } for result in results]
    logger.info(f"Tavily search results: {formatted_results}")
    return formatted_results

def logged_combined_search(*args, **kwargs):
    logger.info(f"Executing Combined search with args: {args}, kwargs: {kwargs}")
    # Get results from both sources
    google_results = logged_google_search(*args, **kwargs)
    tavily_results = logged_tavily_search(*args, **kwargs)
    
    # Combine results while maintaining source attribution
    combined_results = google_results + tavily_results
    
    # Log the combined results
    logger.info(f"Combined search results: {combined_results}")
    return combined_results

# Replace the original functions with logged versions
google_search = logged_google_search
tavily_search = logged_tavily_search
combined_search = logged_combined_search