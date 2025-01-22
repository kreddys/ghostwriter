"""Graph implementation for the GhostWriter system."""
import logging
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from ghostwriter.state import State, InputState
from ghostwriter.agents.article_writer import article_writer_agent
from ghostwriter.tools.checker import uniqueness_checker
from ghostwriter.utils.search.enrich import search_enricher
from ghostwriter.tools.searcher import process_search
from ghostwriter.tools.publisher import publish_to_ghost
from ghostwriter.utils.unique.url_store import store_urls
from ghostwriter.configuration import Configuration
from typing import Literal

logger = logging.getLogger(__name__)

def check_search_status(state: State) -> str:
    """Check if search was successful and determine next step."""
    if not state.search_successful:
        logger.info("Search was unsuccessful, ending workflow")
        return "end"
    logger.info("Search was successful, continuing to check uniqueness")
    return "check_uniqueness"

def should_generate_articles(state: State) -> Literal["next_step", "end"]:
    """Determine if we should proceed with article generation."""
    if not hasattr(state, 'unique_results') or not state.unique_results:
        logger.info("No unique results found - stopping the process")
        return "end"
    
    total_results = sum(len(results) for results in state.unique_results.values() if isinstance(results, list))
    if total_results == 0:
        logger.info("No unique results to process - stopping the process")
        return "end"
        
    logger.info(f"Found {total_results} unique results - proceeding to next step")
    return "next_step"


def determine_next_step(state: State, config: RunnableConfig) -> dict:
    """Determine whether to use search enricher or go directly to generate."""
    configuration = Configuration.from_runnable_config(config)
    if configuration.use_search_enricher:
        logger.info("Search enrichment enabled, proceeding to enrich search")
        return {"next": "enrich_search"}
    logger.info("Search enrichment disabled, proceeding directly to generation")
    return {"next": "generate"}

def create_graph() -> StateGraph:
    """Create the graph with search, article generation, and publishing steps."""
    workflow = StateGraph(State, input=InputState)
    
    # Add the nodes
    workflow.add_node("search", process_search)
    workflow.add_node("check_uniqueness", uniqueness_checker)
    workflow.add_node("next_step", determine_next_step)
    workflow.add_node("enrich_search", search_enricher)
    workflow.add_node("generate", article_writer_agent)
    workflow.add_node("publish", publish_to_ghost)
    workflow.add_node("store_urls", store_urls)
    
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
            "next_step": "next_step",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "next_step",
        lambda state, config: determine_next_step(state, config)["next"],
        {
            "enrich_search": "enrich_search",
            "generate": "generate"
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
