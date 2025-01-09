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
from ..tools.ghost_api import fetch_ghost_tags, GhostTag, fetch_ghost_articles, GhostArticle

from ..state import State
from ..configuration import Configuration

logger = logging.getLogger(__name__)


async def article_writer_agent(
    state: State,
    config: RunnableConfig,
) -> State:  # Changed return type to State
    """
    Agent that processes search results and generates articles in Ghost-compatible format.

    Args:
        state: Current state containing search results and messages
        config: Configuration for the agent

    Returns:
        Updated state containing generated articles
    """
    logger.info("Starting Article Writer Agent")

    configuration = Configuration.from_runnable_config(config)
    logger.info(f"Using model: {configuration.model}")

    # Fetch Ghost CMS tags
    app_url = os.getenv("GHOST_APP_URL")
    ghost_api_key = os.getenv("GHOST_API_KEY")
    
    if not app_url:
        raise ValueError("GHOST_APP_URL environment variable not set")
    if not ghost_api_key:  # Add this check
        raise ValueError("GHOST_API_KEY environment variable not set")
    
    ghost_tags = await fetch_ghost_tags(app_url, ghost_api_key)
    tag_names = [tag.name for tag in ghost_tags]

    existing_articles = await fetch_ghost_articles(app_url, ghost_api_key)
    existing_articles_text = "\n\n".join([
        f"Title: {article.title}\nContent: {article.content}"
        for article in existing_articles
    ])

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
            model=configuration.model.split("/")[1],
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
    search_results_text = "\n\n".join(
        [
            f"Title: {result.get('title', 'N/A')}\nContent: {result.get('content', 'N/A')}"
            for result in all_results
        ]
    )

    messages = [
        SystemMessage(
            content=f"""You are a skilled writer and content organizer. Your task is to analyze the search results and existing articles, then create only NEW articles that don't overlap with existing content.

                EXISTING ARTICLES:
                {existing_articles_text}

                INSTRUCTIONS:
                1. Review the existing articles carefully, especially checking for any content that is alredy existing
                2. Analyze the search results for new, unique topics
                3. Only create articles for topics that aren't already covered
                4. For each potential article, explain your reasoning about why it's fresh content
                5. Each new article should follow this format:

                Available tags (use only these):
                {', '.join(tag_names)}

                [ARTICLE_START]
                # <article title>

                <meta description - compelling summary in 150-160 characters>

                ## Tags
                - Choose 2-3 most relevant tags from the list
                - Tags must match exactly as shown above

                ## Content
                <article content in pure markdown>
                [ARTICLE_END]

                Separate multiple articles with '==='

                IMPORTANT:
                - If a topic is already covered in existing articles, skip it
                - Only generate completely fresh content
                - Explain your reasoning for each article you choose to generate
                """
        ),
        HumanMessage(
            content=f"Generate fresh articles from these search results:\n\n{search_results_text}"
        ),
    ]

    # Generate response using the model
    response = await model.ainvoke(messages)
    formatted_response = response.content

    # Store the generated articles in state
    if not hasattr(state, "articles"):
        state.articles = {}

    state.articles["messages"] = [AIMessage(content=formatted_response)]
    logger.info(f"Generated and stored articles in state")

    return state

