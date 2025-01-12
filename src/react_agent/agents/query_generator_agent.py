"""Query Generator Agent implementation."""
import os
import logging
from typing import Annotated, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

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
        if configuration.model.startswith("deepseek/"):
            logger.info("Initializing DeepSeek model")
            llm = ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
                openai_api_base="https://api.deepseek.com/v1",
                temperature=0.8,
                max_tokens=4096,
            )
        else:
            logger.info("Initializing Ollama model")
            llm = ChatOllama(
                model=configuration.model.split("/")[1],
                base_url="http://host.docker.internal:11434",
                temperature=0.8,
                num_ctx=8192,
                num_predict=4096,
            )

        # Format prompts
        system_prompt = QUERY_GENERATOR_SYSTEM_PROMPT
        user_prompt = QUERY_GENERATOR_USER_PROMPT.format(
            user_input=user_input
        )

        # Get LLM response
        response = await llm.ainvoke(
            {
                "system": system_prompt,
                "user": user_prompt
            },
            config=config
        )

        # Parse queries from response
        queries = [
            q.strip() for q in response.content.split('\n') 
            if q.strip() and not q.startswith('-')
        ]

        # Validate and clean queries
        valid_queries = []
        for query in queries:
            if len(query) > 0 and len(query) <= 256:  # reasonable length limit
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
        # Fallback to original query if generation fails
        return [user_input]