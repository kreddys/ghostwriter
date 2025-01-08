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
from react_agent.tools.slack_sender import slack_sender

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

async def publish_to_slack(
    articles: Dict[str, List[AIMessage]], 
    config: RunnableConfig,
    state: State
) -> Dict[str, List[AIMessage]]:
    """
    Publish articles to Slack and return the original articles.
    
    Args:
        articles: Dictionary containing articles as AIMessages
        config: Configuration for the tool
        state: Current state
    
    Returns:
        The input articles dictionary
    """
    logger.info("Starting Slack publication process")
    
    try:
        await slack_sender(articles, config=config, state=state)
        logger.info("Successfully published articles to Slack")
    except Exception as e:
        logger.error(f"Error publishing to Slack: {str(e)}")
        # Continue execution even if Slack publishing fails
        
    return articles

def create_graph() -> StateGraph:
    """Create the graph with search, article generation, and publishing steps."""
    logger.info("Starting graph creation")
    
    workflow = StateGraph(State, input=InputState)
    
    # Add the nodes
    workflow.add_node("search", process_search)
    workflow.add_node("generate", article_writer_agent)
    workflow.add_node("publish", publish_to_slack)
    
    # Add the edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "generate")
    workflow.add_edge("generate", "publish")
    workflow.set_finish_point("publish")
    
    logger.info("Graph creation complete")
    return workflow.compile()