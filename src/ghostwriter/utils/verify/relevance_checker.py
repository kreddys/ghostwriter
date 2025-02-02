import logging
from typing import Optional
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from ...llm import get_llm
from ...configuration import Configuration
from ...prompts import RELEVANCY_CHECK_PROMPT  # Import the relevancy check prompt

logger = logging.getLogger(__name__)

class RelevanceChecker:
    def __init__(self, topic, threshold, configuration):
        self.topic = topic
        self.threshold = threshold
        self.configuration = configuration
        self.llm = get_llm(configuration)

    async def is_relevant(self, content):
        # Use LLM to determine relevance
        relevance = await self.check_relevance_with_llm(content)
        return relevance >= self.threshold

    async def check_relevance_with_llm(self, content):
        # Define the prompt for the LLM
        prompt = RELEVANCY_CHECK_PROMPT.format(topic=self.topic, content=content)
        
        # Create SystemMessage
        messages = [
            SystemMessage(
                content=prompt
            )
        ]
        
        # Call the LLM
        try:
            response = await self.llm.ainvoke(messages)
            summary = response.content
        except Exception as e:
            logger.error(f"LLM relevance check failed: {e}")
            return 0
        
        # Parse the response
        if "relevant" in summary.lower():
            relevance_score = 1
        else:
            relevance_score = 0
        
        return relevance_score
