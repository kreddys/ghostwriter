import os
import logging
from typing import Any, Dict, List, Literal
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.tools.combined_search import combined_search

logger = logging.getLogger(__name__)

async def search_web(state: State, config: RunnableConfig) -> State:
    """First step: Search the web for articles using both Tavily and Google."""
    logger.info("Starting web search step")
    
    # Initialize search results dictionary if not exists
    if not hasattr(state, 'search_results'):
        state.search_results = {}
        logger.info("Initialized empty search_results in state")
    
    # Get the query from the first message
    if state.messages:
        query = state.messages[0].content
        logger.info(f"Processing search query: {query}")
        
        # Execute combined search
        results = await combined_search(query, config=config, state=state)
        logger.info(f"Received {len(results) if results else 0} search results")
        
        # Store results in state
        if results:
            normalized_query = query.lower()
            state.search_results[normalized_query] = results
            logger.info(f"Stored results for query: {normalized_query}")
    
    logger.info("Completed web search step")
    return state

async def generate_article(state: State, config: RunnableConfig) -> Dict[str, List[AIMessage]]:
    """Second step: Generate multiple articles from search results, organized by topic."""
    logger.info("Starting article generation step")
    
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
    
    logger.info("Completed article generation step")
    return {"messages": [AIMessage(content=formatted_response)]}

def create_graph() -> StateGraph:
    """Create the graph with two simple steps: search and generate."""
    logger.info("Starting graph creation")
    
    # Initialize with both State and InputState
    workflow = StateGraph(State, input=InputState)
    logger.info("Initialized StateGraph")
    
    # Add the nodes
    workflow.add_node("search", search_web)
    workflow.add_node("generate", generate_article)
    logger.info("Added search and generate nodes")
    
    # Add the edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "generate")
    workflow.set_finish_point("generate")
    logger.info("Added edges and set entry/finish points")
    
    logger.info("Compiling graph")
    compiled_graph = workflow.compile()
    logger.info("Graph compilation complete")
    
    return compiled_graph

# Create the graph instance
graph = create_graph()