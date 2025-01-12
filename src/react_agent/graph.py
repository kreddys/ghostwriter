"""Graph implementation for the React Agent."""
import logging
from langgraph.graph import StateGraph, END
from react_agent.state import State, InputState
from react_agent.agents.article_writer import article_writer_agent
from react_agent.tools.uniqueness_checker import uniqueness_checker
from react_agent.workflows.search_processor import process_search
from react_agent.workflows.ghost_publisher import publish_to_ghost
from react_agent.workflows.url_storage import store_urls_in_supabase
from react_agent.workflows.article_generation import should_generate_articles

logger = logging.getLogger(__name__)

def create_graph() -> StateGraph:
    """Create the graph with search, article generation, and publishing steps."""
    logger.info("Starting graph creation")
    
    workflow = StateGraph(State, input=InputState)
    
    # Add the nodes
    workflow.add_node("search", process_search)
    workflow.add_node("check_uniqueness", uniqueness_checker)
    workflow.add_node("generate", article_writer_agent)
    workflow.add_node("publish", publish_to_ghost)
    workflow.add_node("store_urls", store_urls_in_supabase)
    
    # Add conditional routing after uniqueness check
    workflow.add_conditional_edges(
        "check_uniqueness",
        should_generate_articles,
        {
            "generate": "generate",
            "end": END
        }
    )
    
    # Add the other edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "check_uniqueness")
    workflow.add_edge("generate", "publish")
    workflow.add_edge("publish", "store_urls")
    workflow.add_edge("store_urls", END)

    return workflow.compile()

# Create the graph instance
graph = create_graph()