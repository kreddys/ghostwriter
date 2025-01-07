"""Define a custom Reasoning and Action agent."""
import os
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
from react_agent.tools import search

async def search_web(state: State, config: RunnableConfig) -> State:
    """First step: Search the web for articles."""
    # Initialize search results dictionary if not exists
    if not hasattr(state, 'search_results'):
        state.search_results = {}
    
    # Get the query from the first message
    if state.messages:
        query = state.messages[0].content
        results = await search(query, config=config, state=state)
        
        # Store results in state
        if results:
            normalized_query = query.lower()
            state.search_results[normalized_query] = results
    
    return state

async def generate_article(state: State, config: RunnableConfig) -> Dict[str, List[AIMessage]]:
    """Second step: Generate consolidated article from search results."""
    configuration = Configuration.from_runnable_config(config)
    
    if configuration.model.startswith("deepseek/"):
        model = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="https://api.deepseek.com/v1",
            temperature=0.8,
            max_tokens=4096,
        )
    else:
        model = ChatOllama(
            model=configuration.model.split('/')[1],
            base_url="http://host.docker.internal:11434",
            temperature=0.8,
            num_ctx=8192,
            num_predict=4096,
        )

    # Get all search results
    all_results = []
    for results in state.search_results.values():
        if isinstance(results, list):
            all_results.extend(results)

    # Create prompt with search results
    search_results_text = "\n\n".join([
        f"Title: {result.get('title', 'N/A')}\nContent: {result.get('content', 'N/A')}"
        for result in all_results
    ])

    messages = [
        SystemMessage(content="You are a skilled writer. Using the provided search results, "
                            "create a well-organized, comprehensive article that synthesizes "
                            "the information. Use a professional tone and ensure the article "
                            "flows naturally."),
        HumanMessage(content=f"Here are the search results:\n\n{search_results_text}\n\n"
                            f"Please create a consolidated article based on these results.")
    ]

    response = await model.ainvoke(messages)
    return {"messages": [response]}

def create_graph() -> StateGraph:
    """Create the graph with two simple steps: search and generate."""
    # Initialize with both State and InputState
    workflow = StateGraph(State, input=InputState)
    
    # Add the nodes
    workflow.add_node("search", search_web)
    workflow.add_node("generate", generate_article)
    
    # Add the edges
    workflow.set_entry_point("search")
    workflow.add_edge("search", "generate")
    workflow.set_finish_point("generate")
    
    return workflow.compile()

# Create the graph instance
graph = create_graph()