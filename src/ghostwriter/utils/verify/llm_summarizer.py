import logging
import asyncio
from langchain_core.messages import SystemMessage
from typing import Optional
from ...llm import get_llm
from ...configuration import Configuration
from ...prompts import LLM_SUMMARIZER_PROMPT

logger = logging.getLogger(__name__)

async def summarize_content(
    content: str,
    configuration: Configuration,
    max_length: int = 500,
    temperature: float = 0.8,
    max_retries: int = 3,  # Configurable number of retries
    retry_delay: float = 1.0,  # Delay between retries in seconds
) -> Optional[str]:
    """Summarizes content using an LLM with retry logic.

    Args:
        content: The text to summarize.
        configuration: The configuration object for LLM initialization.
        max_length: The maximum length of the summarized text.
        temperature: The temperature parameter for the LLM.
        max_retries: Maximum number of retries in case of failure.
        retry_delay: Delay between retries in seconds.

    Returns:
        The summarized text, or None if all retries fail.
    """
    llm = get_llm(configuration, temperature=temperature)
    messages = [
        SystemMessage(
            content=LLM_SUMMARIZER_PROMPT.format(content=content)
        )
    ]

    for attempt in range(max_retries):
        try:
            response = await llm.ainvoke(messages)
            summary = response.content
            if summary:  # Ensure the response is not empty
                return summary[:max_length]
            else:
                logger.warning(f"Attempt {attempt + 1}: Empty summary generated.")
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}: LLM summarization failed: {e}")
            if attempt < max_retries - 1:  # No delay needed on the last attempt
                await asyncio.sleep(retry_delay)  # Add delay between retries

    logger.error(f"All {max_retries} attempts failed for LLM summarization.")
    return None