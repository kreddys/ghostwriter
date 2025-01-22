"""Graph implementation for the GhostWriter system."""
import logging
from langgraph.graph import StateGraph, END
from ghostwriter.state import State, InputState
from ghostwriter.agents.article_writer import article_writer_agent
from ghostwriter.tools.checker import uniqueness_checker
from ghostwriter.tools.searcher import process_search
from ghostwriter.tools.scraper import process_scrape
from ghostwriter.tools.publisher import publish_to_ghost
from ghostwriter.tools.notify import notify
from typing import Literal

logger = logging.getLogger(__name__)

def check_search_status(state: State) -> str:
    """Check if search was successful and determine next step."""
    searcher_state = state.tool_states.get('searcher', {})
    search_successful = searcher_state.get('search_successful', False)
    
    if not search_successful:
        logger.info("Search was unsuccessful, ending workflow")
        return "end"
    logger.info("Search was successful, routing to scrape")
    return "scrape"

def should_generate_articles(state: State) -> Literal["generate", "end"]:
    """Determine if we should proceed with article generation."""
    checker_state = state.tool_states.get('checker', {})
    unique_results = checker_state.get('unique_results', {})
    
    if not unique_results:
        logger.info("No unique results found - stopping the process")
        return "end"
    
    total_results = sum(len(results) for results in unique_results.values() if isinstance(results, list))
    if total_results == 0:
        logger.info("No unique results to process - stopping the process")
        return "end"
        
    logger.info(f"Found {total_results} unique results - proceeding to generate articles")
    return "generate"

def create_graph() -> StateGraph:
    """Create the graph with search, article generation, and publishing steps."""
    workflow = StateGraph(State, input=InputState)
    
    # Add the nodes
    workflow.add_node("search", process_search)
    workflow.add_node("scrape", process_scrape)
    workflow.add_node("verify", uniqueness_checker)
    workflow.add_node("generate", article_writer_agent)
    workflow.add_node("publish", publish_to_ghost)
    workflow.add_node("notify", notify)
    
    # Add conditional routing after search to check search_successful
    workflow.add_conditional_edges(
        "search",
        check_search_status,
        {
            "scrape": "scrape",
            "end": END
        }
    )
    
    # Add edge from scrape to verify
    workflow.add_edge("scrape", "verify")
    
    # Add conditional routing after uniqueness check
    workflow.add_conditional_edges(
        "verify",
        should_generate_articles,
        {
            "generate": "generate",
            "end": END
        }
    )
    
    # Add the other edges
    workflow.set_entry_point("search")
    workflow.add_edge("generate", "publish")
    workflow.add_edge("publish", "notify")
    workflow.add_edge("notify", END)
    
    return workflow.compile()

# Create the graph instance
graph = create_graph()
