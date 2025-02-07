"""Define the state structures for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from langchain_core.messages import AnyMessage, AIMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from typing_extensions import Annotated


@dataclass
class InputState:
    """Defines the input state for the agent, representing a narrower interface to the outside world.

    This class is used to define the initial state and structure of incoming data.
    """

    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )
    """
    Messages tracking the primary execution state of the agent.

    Typically accumulates a pattern of:
    1. HumanMessage - user input
    2. AIMessage with .tool_calls - agent picking tool(s) to use to collect information
    3. ToolMessage(s) - the responses (or errors) from the executed tools
    4. AIMessage without .tool_calls - agent responding in unstructured format to the user
    5. HumanMessage - user responds with the next conversational turn

    Steps 2-5 may repeat as needed.

    The `add_messages` annotation ensures that new messages are merged with existing ones,
    updating by ID to maintain an "append-only" state unless a message with the same ID is provided.
    """


@dataclass
class State(InputState):
    """Represents the complete state of the agent, extending InputState with additional attributes."""
    
    # Raw search results from web search
    search_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    
    # Results after URL filtering
    url_filtered_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    
    # Results after uniqueness checking
    unique_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    
    # Keep existing fields
    articles: dict[str, list[AIMessage]] = field(default_factory=dict)
    
    # Enriched Results of a unique search item
    enriched_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    search_successful: bool = False

    topic: str = "Amaravati, Andhra Pradesh Capital City"  # Add this field for the configured topic

    is_direct_url: bool = False  # Add this field to indicate direct URL processing

    direct_url: str = ""  # Store the direct URL if provided