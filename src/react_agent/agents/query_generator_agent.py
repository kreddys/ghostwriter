"""Query Generator Agent implementation."""
import logging
from typing import Annotated, List
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from ..state import State
from ..prompts import QUERY_GENERATOR_SYSTEM_PROMPT, QUERY_GENERATOR_USER_PROMPT

logger = logging.getLogger(__name__)

class QueryGeneratorAgent:
    """Agent for generating multiple search queries from user input."""

    def __init__(self, state: State):
        """Initialize QueryGeneratorAgent."""
        self.state = state
        self.llm = state.llm

    async def generate_queries(
        self,
        user_input: str,
        *,
        config: Annotated[RunnableConfig, InjectedToolArg]
    ) -> List[str]:
        """Generate multiple search queries from user input."""
        try:
            # Format prompts
            system_prompt = QUERY_GENERATOR_SYSTEM_PROMPT
            user_prompt = QUERY_GENERATOR_USER_PROMPT.format(
                user_input=user_input
            )

            # Get LLM response
            response = await self.llm.ainvoke(
                {
                    "system": system_prompt,
                    "user": user_prompt
                },
                config=config
            )

            # Parse queries from response
            queries = [
                q.strip() for q in response.split('\n') 
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
            self.state.generated_queries = valid_queries
            self.state.original_input = user_input

            logger.info(f"Generated {len(valid_queries)} search queries: {valid_queries}")
            return valid_queries

        except Exception as e:
            logger.error(f"Error generating search queries: {str(e)}")
            # Fallback to original query if generation fails
            return [user_input]