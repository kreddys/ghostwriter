"""Graph implementation for the React Agent."""
import logging
from langgraph.graph import StateGraph, END
from react_agent.state import State, InputState
from react_agent.agents.article_writer import article_writer_agent
from react_agent.tools.uniqueness_checker import uniqueness_checker
from react_agent.tools.search_enricher import search_enricher
from react_agent.workflows.search_processor import process_search
from react_agent.workflows.ghost_publisher import publish_to_ghost
from react_agent.workflows.url_storage import store_urls_in_supabase
from react_agent.workflows.article_generation import should_generate_articles

logger = logging.getLogger(__name__)

def check_search_status(state: State) -> str:
    """Check if search was successful and determine next step."""
    if not state.search_successful:
        logger.info("Search was unsuccessful, ending workflow")
        return "end"
    logger.info("Search was successful, continuing to check uniqueness")
    return "check_uniqueness"

def create_graph() -> StateGraph:
    """Create the graph with search, article generation, and publishing steps."""
    workflow = StateGraph(State, input=InputState)
    
    # Add the nodes
    workflow.add_node("search", process_search)
    workflow.add_node("check_uniqueness", uniqueness_checker)
    workflow.add_node("enrich_search", search_enricher)
    workflow.add_node("generate", article_writer_agent)
    workflow.add_node("publish", publish_to_ghost)
    workflow.add_node("store_urls", store_urls_in_supabase)
    
    # Add conditional routing after search to check search_successful
    workflow.add_conditional_edges(
        "search",
        check_search_status,
        {
            "check_uniqueness": "check_uniqueness",
            "end": END
        }
    )
    
    # Add conditional routing after uniqueness check
    workflow.add_conditional_edges(
        "check_uniqueness",
        should_generate_articles,
        {
            "generate": "enrich_search",
            "end": END
        }
    )
    
    # Add the other edges
    workflow.set_entry_point("search")
    workflow.add_edge("enrich_search", "generate")
    workflow.add_edge("generate", "publish")
    workflow.add_edge("publish", "store_urls")
    workflow.add_edge("store_urls", END)
    
    return workflow.compile()

# Create the graph instance
graph = create_graph()