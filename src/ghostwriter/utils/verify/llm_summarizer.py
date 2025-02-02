import logging
from typing import Optional
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from ...llm import get_llm
from ...configuration import Configuration
from ...prompts import LLM_SUMMARIZER_PROMPT  # Import the summarizer prompt

logger = logging.getLogger(__name__)

async def summarize_content(content: str, configuration: Configuration, max_length: int = 500, temperature: float = 0.8) -> Optional[str]:
    """Summarizes content using an LLM.

    Args:
        content: The text to summarize.
        configuration: The configuration object for LLM initialization.
        max_length: The maximum length of the summarized text.
        temperature: The temperature parameter for the LLM.

    Returns:
        The summarized text, or None if an error occurs.
    """
    try:
        llm = get_llm(configuration, temperature=temperature)
        messages = [
            SystemMessage(
                content=LLM_SUMMARIZER_PROMPT.format(content=content)
            )
        ]
        response = await llm.ainvoke(messages)
        summary = response.content
        return summary[:max_length]
    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        return None
