"""Graph implementation for the React Agent."""
import logging
from typing import Any, Dict, List, Literal
from datetime import datetime, timezone
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langchain_core.messages import AIMessage

from react_agent.state import State, InputState
from react_agent.agents.article_writer import article_writer_agent
from react_agent.tools.combined_search import combined_search
from react_agent.tools.ghost_publisher import ghost_publisher

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

async def publish_to_ghost(state: State, config: RunnableConfig) -> State:
    """
    Publish articles to Ghost as drafts and notify via Slack.
    """
    logger.info("Starting Ghost publication process")
    
    try:
        if hasattr(state, 'articles') and state.articles:
            logger.info(f"Found {len(state.articles.get('messages', []))} articles to publish")
            success = await ghost_publisher(state.articles, config=config, state=state)
            if success:
                logger.info("Successfully published articles to Ghost")
            else:
                logger.error("Failed to publish some articles to Ghost")
        else:
            logger.warning("No articles found in state to publish")
    except Exception as e:
        logger.error(f"Error publishing to Ghost: {str(e)}")
        
    return state

def create_graph() -> StateGraph:
    """Create the graph with search, article generation, and publishing steps."""
    logger.info("Starting graph creation")
    
    workflow = StateGraph(State, input=InputState)
    
    # Add the nodes
    workflow.add_node("search", process_search)
    workflow.add_node("generate", article_writer_agent)
    workflow.add_node("publish", publish_to_ghost)
    
    # Add the edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "generate")
    workflow.add_edge("generate", "publish")
    workflow.set_finish_point("publish")
    
    logger.info("Graph creation complete")
    return workflow.compile()

# Create the graph instance
graph = create_graph()