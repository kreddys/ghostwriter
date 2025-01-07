"""Default prompts used by the agent."""

SYSTEM_PROMPT = """You are a helpful assistant. Current time: {system_time}

When searching for recent information:
- Use a single, comprehensive search query
- Avoid making multiple similar searches with different time frames
- Consolidate time-based queries into one search using "recent" or "latest"
"""
