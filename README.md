# Content Curation and Publishing Agent

A sophisticated content curation and publishing system built with LangGraph that
uses ReAct (Reasoning and Action) agents to search, filter, and process content
while ensuring uniqueness and relevance.

## Features

- Multi-source content search using various search engines (Tavily, Google,
  SERP)
- Content uniqueness verification using Pinecone vector database
- Relevancy checking using advanced language models
- Integration with Ghost CMS for content publishing
- Slack integration for notifications and updates
- Configurable search parameters and filtering options
- URL filtering against existing content
- Search result enrichment capabilities

## Prerequisites

- Python 3.9 or higher
- Required API keys:
  - Tavily API key
  - Anthropic API key (default) or OpenAI API key
  - Pinecone API key
  - Ghost CMS API key (if using Ghost integration)
  - Slack API key (if using Slack integration)
  - Google Custom Search API key (if using Google search)
