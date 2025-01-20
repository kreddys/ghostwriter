"""Centralized LLM initialization module."""
import os
import logging
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from .configuration import Configuration

logger = logging.getLogger(__name__)

def get_llm(configuration: Configuration, temperature: float = 0.8, max_tokens: int = 4096):
    """
    Get the appropriate LLM based on configuration.
    
    Args:
        configuration: Configuration object containing model settings
        temperature: Temperature setting for the model
        max_tokens: Maximum tokens for the response
        
    Returns:
        Configured LLM instance
    """
    logger.info(f"Initializing LLM with model: {configuration.model}")
    
    if configuration.model.startswith("deepseek/"):
        logger.info("Initializing DeepSeek model")
        return ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="https://api.deepseek.com/v1",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        logger.info("Initializing Ollama model")
        return ChatOllama(
            model=configuration.model.split("/")[1],
            base_url="http://host.docker.internal:11434",
            temperature=temperature,
            num_ctx=max_tokens * 2,  # Ollama uses context window instead of max_tokens
            num_predict=max_tokens,
        )