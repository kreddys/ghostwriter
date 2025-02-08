"""Define the configurable parameters for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Annotated, Optional

from langchain_core.runnables import RunnableConfig, ensure_config

from ghostwriter import prompts


@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    llm_model: str = field(
        default="google/gemini-2.0-flash-lite-preview-02-05:free",
        metadata={
            "description": "The name of the LLM model to use"
        }
    )
    
    embedding_model: str = field(
        default="multilingual-e5-large",
        metadata={
            "description": "The name of the Embedding model to use"
        }
    )

    search_engines: list[str] = field(
        default_factory=lambda: ["google", "tavily", "serp", "youtube"],
        metadata={
            "description": "List of search engines to use. Options: 'google', 'tavily', 'serp', 'youtube'. "
            "Empty list will use all available engines."
        },
    )

    max_search_results: int = field(
        default=10,
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

    similarity_threshold: float = field(
        default=0.85,
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

    scraping_engines: list[str] = field(
        default_factory=lambda: ["firecrawl","youtube"],
        metadata={
            "description": "List of scraping engines to use. Options: 'firecrawl', 'youtube'. "
            "Empty list will use all available engines."
        },
    )

    topic: str = field(
        default="Amaravati Capital City, Andhra Pradesh",
        metadata={
            "description": "The topic to focus on for content generation and filtering"
        }
    )

    skip_uniqueness_checker: bool = field(
        default=True,
        metadata={
            "description": "Whether to check for unique posts in ghost website"
        }
    )

    chunk_size: int = 500
    chunk_overlap: int = 50

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})
