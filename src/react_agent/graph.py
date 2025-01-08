import logging
from typing import Any, Dict, List, Literal
from datetime import datetime, timezone
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

from .state import State, InputState
from .agents.article_writer import article_writer_agent
from .tools.combined_search import combined_search

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

def create_graph() -> StateGraph:
    """Create the graph with two simple steps: search and generate."""
    logger.info("Starting graph creation")
    
    # Initialize with both State and InputState
    workflow = StateGraph(State, input=InputState)
    logger.info("Initialized StateGraph")
    
    # Add the nodes
    workflow.add_node("search", search_web)
    workflow.add_node("generate", article_writer_agent)
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