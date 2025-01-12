"""Graph implementation for the React Agent."""
import logging
from typing import Any, Dict, List, Literal
from datetime import datetime, timezone
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from react_agent.state import State, InputState
from react_agent.agents.article_writer import article_writer_agent
from react_agent.tools.combined_search import combined_search
from react_agent.tools.ghost_publisher import ghost_publisher
from react_agent.tools.supabase_url_store import supabase_url_store
from react_agent.tools.uniqueness_checker import uniqueness_checker
from react_agent.agents.query_generator_agent import generate_queries

logger = logging.getLogger(__name__)

async def process_search(state: State, config: RunnableConfig) -> State:
    """Execute search using combined search functionality with multiple generated queries."""
    logger.info("Starting search process")
    
    if not state.messages:
        logger.warning("No messages found in state")
        return state
        
    query = state.messages[0].content
    logger.info(f"Processing initial query: {query}")
    
    try:
        # Generate multiple search queries using the function
        search_queries = await generate_queries(
            query,
            config=config,
            state=state
        )
        
        # Execute combined search with all queries at once
        try:
            results = await combined_search(
                search_queries,  # Pass all queries at once
                config=config, 
                state=state
            )
            if not results:
                logger.warning("No results found from search queries")
                return state
                
            logger.info(f"Retrieved {len(results)} results from combined search")
            
            # The combined_search now handles:
            # 1. Deduplication by URL
            # 2. Sorting by date
            # 3. Storing in state.raw_search_results
            # 4. Storing in state.unique_results
            
            # Store in search_results for backward compatibility
            state.url_filtered_results[query.lower()] = results
            
        except Exception as e:
            logger.error(f"Error in combined search: {str(e)}")
            return state
            
    except Exception as e:
        logger.error(f"Error in process_search: {str(e)}")
        # Don't raise the exception to allow the graph to continue
        # but log it for debugging
    
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

async def store_urls_in_supabase(state: State, config: RunnableConfig) -> State:
    """Store article URLs in Supabase."""
    logger.info("Starting Supabase URL storage process")
    
    try:
        if hasattr(state, 'articles') and state.articles:
            logger.info(f"Found {len(state.articles.get('messages', []))} articles to store URLs")
            success = await supabase_url_store(state.articles, config=config, state=state)
            if success:
                logger.info("Successfully stored URLs in Supabase")
            else:
                logger.error("Failed to store URLs in Supabase")
        else:
            logger.warning("No articles found in state to store URLs")
    except Exception as e:
        logger.error(f"Error storing URLs in Supabase: {str(e)}")
        
    return state

def should_generate_articles(state: State) -> Literal["generate", "end"]:
    """Determine if we should proceed with article generation."""
    if not hasattr(state, 'unique_results') or not state.unique_results:
        logger.info("No unique results found - stopping the process")
        return "end"
    
    total_results = sum(len(results) for results in state.unique_results.values() if isinstance(results, list))
    if total_results == 0:
        logger.info("No unique results to process - stopping the process")
        return "end"
        
    logger.info(f"Found {total_results} unique results - proceeding with article generation")
    return "generate"

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
            "end": END  # Use END instead of workflow.end
        }
    )
    
    # Add the other edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "check_uniqueness")
    workflow.add_edge("generate", "publish")
    workflow.add_edge("publish", "store_urls")
    workflow.add_edge("store_urls", END)  # Add edge to END

    return workflow.compile()

# Create the graph instance
graph = create_graph()