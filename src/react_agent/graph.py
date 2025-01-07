"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

from datetime import datetime, timezone
from typing import Dict, List, Literal, cast

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.tools import TOOLS


async def call_model(state: State, config: RunnableConfig) -> Dict[str, List[AIMessage]]:
    """Call the LLM powering our "agent"."""
    configuration = Configuration.from_runnable_config(config)

    if configuration.model.startswith("deepseek/"):
        # Initialize DeepSeek model using OpenAI-compatible interface
        model = ChatOpenAI(
            model="deepseek-chat",  # DeepSeek's model name
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="https://api.deepseek.com/v1",  # DeepSeek's API endpoint
            temperature=0.8,
            max_tokens=4096,
        ).bind_tools(TOOLS)
    else:
        # Existing Ollama model initialization
        model = ChatOllama(
            model=configuration.model.split('/')[1],
            base_url="http://host.docker.internal:11434",
            temperature=0.8,
            num_ctx=8192,
            num_predict=4096,
        ).bind_tools(TOOLS)

    # Rest of the function remains the same
    system_message = configuration.system_prompt.format(
        system_time=datetime.now(tz=timezone.utc).isoformat()
    )

    response = cast(
        AIMessage,
        await model.ainvoke(
            [{"role": "system", "content": system_message}, *state.messages], config
        ),
    )

    if state.is_last_step and response.tool_calls:
        return {
            "messages": [
                AIMessage(
                    id=response.id,
                    content="Sorry, I could not find an answer to your question in the specified number of steps.",
                )
            ]
        }

    return {"messages": [response]}


# Define the graph
builder = StateGraph(State, input=InputState, config_schema=Configuration)

# Define nodes
builder.add_node(call_model)
builder.add_node("tools", ToolNode(TOOLS))

# Set the entrypoint
builder.add_edge("__start__", "call_model")


def route_model_output(state: State) -> Literal["__end__", "tools"]:
    """Determine the next node based on the model's output."""
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage):
        raise ValueError(
            f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
        )
    # If there is no tool call, then we finish
    if not last_message.tool_calls:
        return "__end__"
    return "tools"


# Add edges for routing
builder.add_conditional_edges("call_model", route_model_output)
builder.add_edge("tools", "call_model")

# Compile the graph
graph = builder.compile()