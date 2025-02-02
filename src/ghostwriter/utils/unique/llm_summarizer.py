import logging
from typing import Optional
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from ...llm import get_llm

logger = logging.getLogger(__name__)

async def summarize_content(content: str, max_length: int = 2000) -> Optional[str]:
    """Summarizes content using an LLM.

    Args:
        content: The text to summarize.
        max_length: The maximum length of the summarized text.

    Returns:
        The summarized text, or None if an error occurs.
    """
    try:
        llm = get_llm()
        prompt_template = "Summarize the following text, extracting its main theme in a concise manner: {content}"
        prompt = PromptTemplate(template=prompt_template, input_variables=["content"])
        summary = llm(prompt.format(content=content))
        return summary[:max_length]
    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        return None
