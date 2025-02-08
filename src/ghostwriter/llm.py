"""Centralized LLM initialization module."""

import os
import logging
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from .configuration import Configuration

logger = logging.getLogger(__name__)


def get_llm(
    configuration: Configuration, temperature: float = 0.8, max_tokens: int = 4096
):
    """
    Get the appropriate LLM based on configuration settings.

    Args:
        configuration: Configuration object containing model settings
        temperature: Temperature setting for the model
        max_tokens: Maximum tokens for the response

    Returns:
        Configured LLM instance
    """
    logger.info(f"Initializing OpenAI-compatible model: {configuration.llm_model}")

    return ChatOpenAI(
        model=configuration.llm_model,  # Use model name from configuration
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_API_BASE"),
        temperature=temperature,
        max_tokens=max_tokens,
    )