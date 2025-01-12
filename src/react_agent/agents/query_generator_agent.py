"""Query Generator Agent implementation."""
import os
import json
import logging
from typing import Annotated, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_core.messages import SystemMessage, HumanMessage
from ..llm import get_llm 

from ..state import State
from ..prompts import QUERY_GENERATOR_SYSTEM_PROMPT, QUERY_GENERATOR_USER_PROMPT
from ..configuration import Configuration

logger = logging.getLogger(__name__)

async def generate_queries(
    user_input: str,
    *,
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: State
) -> List[str]:
    """Generate multiple search queries from user input."""
    try:
        # Get configuration
        configuration = Configuration.from_runnable_config(config)
        logger.info(f"Using model: {configuration.model}")

        # Initialize the appropriate model
        llm = get_llm(configuration, temperature=0.3)

        # Create messages in correct format
        messages = [
            SystemMessage(content=QUERY_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(content=QUERY_GENERATOR_USER_PROMPT.format(
                user_input=user_input
            ))
        ]

        # Get LLM response
        response = await llm.ainvoke(
            messages,
            config=config
        )

        # Parse JSON response
        try:
            queries = json.loads(response.content)
            if not isinstance(queries, list):
                raise ValueError("Response is not a JSON array")
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, falling back to text parsing")
            # Fallback to text parsing if JSON parsing fails
            queries = [
                q.strip() for q in response.content.split('\n') 
                if q.strip() and not q.startswith('-')
            ]

        # Validate and clean queries
        valid_queries = []
        for query in queries:
            if isinstance(query, str) and len(query) > 0 and len(query) <= 256:
                valid_queries.append(query)

        if not valid_queries:
            logger.warning("No valid queries generated, falling back to original input")
            valid_queries = [user_input]

        # Store generated queries in state
        state.generated_queries = valid_queries
        state.original_input = user_input

        logger.info(f"Generated {len(valid_queries)} search queries: {valid_queries}")
        return valid_queries

    except Exception as e:
        logger.error(f"Error generating search queries: {str(e)}")
        return [user_input]