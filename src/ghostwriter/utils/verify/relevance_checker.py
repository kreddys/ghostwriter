import logging
import asyncio
from langchain_core.messages import SystemMessage
from typing import Optional
from ...llm import get_llm
from ...configuration import Configuration
from ...prompts import RELEVANCY_CHECK_PROMPT

logger = logging.getLogger(__name__)

class RelevanceChecker:
    def __init__(self, topic, threshold, configuration, max_retries=3, retry_delay=1.0):
        self.topic = topic
        self.threshold = threshold
        self.configuration = configuration
        self.llm = get_llm(configuration)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def is_relevant(self, summarized_content):
        # Use summarized content to determine relevance
        return await self.check_relevance(summarized_content) >= self.threshold

    async def check_relevance(self, summarized_content) -> int:
        """Checks the relevance of the summarized content using an LLM with retry logic."""
        prompt = RELEVANCY_CHECK_PROMPT.format(topic=self.topic, content=summarized_content)
        messages = [SystemMessage(content=prompt)]

        for attempt in range(self.max_retries):
            try:
                response = await self.llm.ainvoke(messages)
                result = response.content
                return 1 if "relevant" in result.lower() else 0
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}: LLM relevance check failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        logger.error(f"All {self.max_retries} attempts failed for LLM relevance check.")
        return 0
