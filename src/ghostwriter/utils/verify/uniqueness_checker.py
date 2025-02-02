"""Utility for checking uniqueness of search results using LightRAG."""
import os
import logging
import requests
import json
import re
from typing import Dict, Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from ...state import State
from ...configuration import Configuration
from ...utils.verify.url_filter_supabase import filter_existing_urls
from ...prompts import CONTENT_VERIFICATION_PROMPT
from ...utils.verify.checker_utils import truncate_content
from ...utils.verify.llm_summarizer import summarize_content

logger = logging.getLogger(__name__)

async def check_uniqueness(
    result: Dict,
    configuration: Configuration
) -> dict:
    """Check if an individual result is unique using LightRAG.
    
    Args:
        result: Single content result to check for uniqueness
        configuration: Configuration object containing settings
        
    Returns:
        dict: Contains uniqueness check results
    """
    try:
        # Get endpoint and API key
        lightrag_endpoint = os.getenv("LIGHTRAG_ENDPOINT")
        lightrag_apikey = os.getenv("LIGHTRAG_APIKEY")

        if not lightrag_endpoint or not lightrag_apikey:
            logger.error("Missing LightRAG credentials")
            raise ValueError("LIGHTRAG_ENDPOINT or LIGHTRAG_APIKEY not set")

        url = result.get('url', 'No URL')
        title = result.get('title', 'No title')
        content = result.get('content', '')

        if not content.strip():
            logger.error(f"No content found for URL: {url}")
            return {
                'is_unique': False,
                'reason': "No content to check",
                'url': url,
                'title': title
            }

        # Truncate content if too long
        content = truncate_content(content)
        
        # Summarize content using LLM
        summarized_content = await summarize_content(content, configuration, max_length=500, temperature=0.8)

        logger.info(f"Processing summarized content for URL: {url}")
        logger.info(f"Summarized content for URL: {url}\n{summarized_content}")

        # Prepare query data for summarized content
        query_data = {
            "query": CONTENT_VERIFICATION_PROMPT.format(combined_content=summarized_content),
            "mode": "hybrid",
            "stream": False,
            "only_need_context": False,
        }

        # Make API request
        response = requests.post(
            lightrag_endpoint,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": lightrag_apikey,
            },
            json=query_data,
            timeout=configuration.lightrag_timeout
        )
        
        logger.info(f"Response status: {response.status_code}")
        response.raise_for_status()
        
        rag_response = response.json()
        
        # Extract JSON from response
        json_match = re.search(r'```json\n({.*?})\n```', rag_response.get('response', ''), re.DOTALL)
        if not json_match:
            logger.warning("Failed to extract JSON from response")
            return {
                'is_unique': False,
                'reason': "Failed to extract JSON from LightRAG response",
                'url': url,
                'title': title
            }

        uniqueness_info = json.loads(json_match.group(1))
        
        return {
            'is_unique': not uniqueness_info.get('is_present', True),
            'reason': uniqueness_info.get('reason', ''),
            'url': url,
            'title': title
        }

    except Exception as e:
        logger.error(f"Error checking uniqueness: {str(e)}")
        return {
            'is_unique': False,
            'reason': f"Error: {str(e)}",
            'url': url,
            'title': title
        }
