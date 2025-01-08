"""Graph implementation for the React Agent."""
import logging
from typing import Any, Dict, List, Literal
from datetime import datetime, timezone
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

# Change relative imports to absolute imports
from react_agent.state import State, InputState
from react_agent.agents.article_writer import article_writer_agent
from react_agent.tools.combined_search import combined_search

logger = logging.getLogger(__name__)

async def process_search(state: State, config: RunnableConfig) -> State:
    """Execute search using combined search functionality."""
    logger.info("Starting search process")
    
    if not hasattr(state, 'search_results'):
        state.search_results = {}
    
    if state.messages:
        query = state.messages[0].content
        logger.info(f"Processing query: {query}")
        
        results = await combined_search(query, config=config, state=state)
        
        if results:
            state.search_results[query.lower()] = results
            logger.info(f"Stored {len(results)} results for query")
    
    return state

def create_graph() -> StateGraph:
    """Create the graph with search and article generation steps."""
    logger.info("Starting graph creation")
    
    workflow = StateGraph(State, input=InputState)
    
    # Add the nodes
    workflow.add_node("search", process_search)
    workflow.add_node("generate", article_writer_agent)
    
    # Add the edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "generate")
    workflow.set_finish_point("generate")
    
    logger.info("Graph creation complete")
    return workflow.compile()

# Create the graph instance
graph = create_graph()