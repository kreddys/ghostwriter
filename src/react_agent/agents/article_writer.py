"""Article Writer Agent functionality."""
import os
import logging
from typing import Dict, List
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from ..state import State
from ..configuration import Configuration

logger = logging.getLogger(__name__)

async def article_writer_agent(
    state: State,
    config: RunnableConfig,
) -> Dict[str, List[AIMessage]]:
    """
    Agent that processes search results and generates articles based on the input.
    
    Args:
        state: Current state containing search results and messages
        config: Configuration for the agent
    
    Returns:
        Dictionary containing generated articles as AIMessages
    """
    logger.info("Starting Article Writer Agent")
    
    configuration = Configuration.from_runnable_config(config)
    logger.info(f"Using model: {configuration.model}")
    
    # Initialize the appropriate model
    if configuration.model.startswith("deepseek/"):
        logger.info("Initializing DeepSeek model")
        model = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="https://api.deepseek.com/v1",
            temperature=0.8,
            max_tokens=4096,
        )
    else:
        logger.info("Initializing Ollama model")
        model = ChatOllama(
            model=configuration.model.split('/')[1],
            base_url="http://host.docker.internal:11434",
            temperature=0.8,
            num_ctx=8192,
            num_predict=4096,
        )

    # Process search results
    all_results = []
    for results in state.search_results.values():
        if isinstance(results, list):
            all_results.extend(results)
    logger.info(f"Processing {len(all_results)} total search results")

    # Create prompt with search results
    search_results_text = "\n\n".join([
        f"Title: {result.get('title', 'N/A')}\nContent: {result.get('content', 'N/A')}"
        for result in all_results
    ])

    messages = [
        SystemMessage(content="""You are a skilled writer and content organizer. Using the provided search results:
        1. Identify distinct topics or themes in the search results
        2. Create multiple articles, one for each major topic
        3. Each article should have:
           - A clear, descriptive title
           - Well-organized content that synthesizes information from relevant search results
        4. Format each article as:
           [ARTICLE_START]
           Title: <article title>
           Content: <article content>
           [ARTICLE_END]
        
        Use a professional tone and ensure each article flows naturally."""),
        HumanMessage(content=f"Here are the search results:\n\n{search_results_text}\n\n"
                            f"Please create multiple articles, organizing the information by topic.")
    ]

    logger.info("Sending request to language model")
    response = await model.ainvoke(messages)
    logger.info("Received response from language model")
    
    # Process the response
    content = response.content
    articles = []
    
    # Split the content into individual articles
    raw_articles = content.split("[ARTICLE_START]")
    for article in raw_articles:
        if article.strip():
            article = article.split("[ARTICLE_END]")[0].strip()
            if "Title:" in article and "Content:" in article:
                articles.append(article)
    
    logger.info(f"Generated {len(articles)} articles")
    
    # Create formatted response
    formatted_response = "Multiple articles generated from the search results:\n\n"
    formatted_response += "\n\n---\n\n".join(articles)
    
    logger.info("Article Writer Agent completed successfully")
    return {"messages": [AIMessage(content=formatted_response)]}