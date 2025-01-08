"""This module provides example tools for web scraping and search functionality."""
import logging
from .tools.google_search import google_search
from .tools.tavily_search import tavily_search
from .tools.combined_search import combined_search

logger = logging.getLogger(__name__)

# Wrap the search functions to add logging
def logged_google_search(*args, **kwargs):
    logger.info(f"Executing Google search with args: {args}, kwargs: {kwargs}")
    results = google_search(*args, **kwargs)
    logger.info(f"Google search results: {results}")
    return results

def logged_tavily_search(*args, **kwargs):
    logger.info(f"Executing Tavily search with args: {args}, kwargs: {kwargs}")
    results = tavily_search(*args, **kwargs)
    logger.info(f"Tavily search results: {results}")
    return results

def logged_combined_search(*args, **kwargs):
    logger.info(f"Executing Combined search with args: {args}, kwargs: {kwargs}")
    results = combined_search(*args, **kwargs)
    logger.info(f"Combined search results: {results}")
    return results

# Replace the original functions with logged versions
google_search = logged_google_search
tavily_search = logged_tavily_search
combined_search = logged_combined_search