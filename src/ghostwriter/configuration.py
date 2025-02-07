"""Define the configurable parameters for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Annotated, Optional

from langchain_core.runnables import RunnableConfig, ensure_config

from ghostwriter import prompts


@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    system_prompt: str = field(
        default=prompts.SYSTEM_PROMPT,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="deepseek/deepseek-v3",
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Should be in the form: provider/model-name."
        },
    )

    search_engines: list[str] = field(
        default_factory=lambda: ["tavily"], #["google", "tavily", "serp"]
        metadata={
            "description": "List of search engines to use. Options: 'google', 'tavily', 'serp'. "
            "Empty list will use all available engines."
        },
    )

    max_search_results: int = field(
        default=2,
        metadata={
            "description": "The maximum number of search results to return for each search query."
        },
    )

    sites_list: Optional[list[str]] = field(
        default=None,
        metadata={
            "description": "List of websites to search. If None, searches the entire web"
        }
    )
       
    search_days: int = field(
        default=7,
        metadata={
            "description": "Number of days to look back for search results"
        }
    )

    slack_enabled: bool = field(
        default=True,
        metadata={
            "description": "Whether to enable Slack integration"
        }
    )
    
    slack_format_code_blocks: bool = field(
        default=True,
        metadata={
            "description": "Whether to format articles as code blocks in Slack"
        }
    )

    use_query_generator: bool = field(
        default=False,
        metadata={"help": "Whether to use query generator or direct search with user input"}
    )

    use_url_filtering: bool = field(
        default=False,
        metadata={
            "description": "Whether to filter out URLs that already exist in Supabase"
        }
    )

    use_search_enricher: bool = field(
        default=False,
        metadata={
            "description": "Whether to use search enricher to find additional relevant content "
            "or directly proceed to article writing with original results"
        }
    )

    similarity_threshold: float = field(
        default=0.80,
        metadata={
            "description": "Threshold for determining content uniqueness using cosine similarity. Used to check existing posts in Ghost & suppress similar posts. "
            "Lower values are more strict (require more uniqueness)."
        },
    )

    relevance_similarity_threshold: float = field(
        default=0.90,
        metadata={
            "description": "Threshold for determining content relevance using cosine similarity. "
            "Higher values are more strict (require more similarity)."
        },
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})
