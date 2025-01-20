# GhostWriter - Automated Content Generation for Ghost CMS

GhostWriter is a sophisticated AI-powered content generation system built with
LangGraph that automates the creation, curation, and publishing of articles to
Ghost CMS. It combines multiple AI technologies and integrations to provide a
complete content generation pipeline.

## Features

- **Multi-source Content Search**: Integrates with various search engines
  (Tavily, Google, SERP)
- **Content Verification**: Uses Pinecone vector database for uniqueness
  verification
- **AI-powered Writing**: Advanced language models for content generation
- **Ghost CMS Integration**: Direct publishing to Ghost CMS
- **Notification System**: Slack integration for updates and notifications
- **Web Interfaces**: FastAPI backend and Streamlit frontend
- **Content Management**: URL filtering and search result enrichment

## Prerequisites

- Python 3.9 or higher
- Docker (optional, for containerized deployment)
- Required API keys (see Setup section)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/ghostwriter.git
   cd ghostwriter
   ```

2. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

3. Configure your environment variables in `.env`:
   ```env
   # Required API Keys
   TAVILY_API_KEY=your_tavily_key
   GHOST_APP_URL=https://your-ghost-instance.com
   GHOST_API_KEY=your_ghost_key
   GHOST_ADMIN_API_KEY=your_admin_key

   # Optional Integrations
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_channel_id
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   PINECONE_API_KEY=your_pinecone_key
   PINECONE_INDEX_NAME=your_index_name
   ```

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. (Optional) Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Running the Application

### FastAPI Backend

Start the FastAPI server:

```bash
uvicorn src.fastapi_app:app --reload
```

Access the API documentation at: http://localhost:8000/docs

### Streamlit Frontend

Start the Streamlit interface:

```bash
streamlit run src/streamlit_app.py
```

Access the UI at: http://localhost:8501

## Testing

Run tests using pytest:

```bash
pytest tests/
```

For integration tests:

```bash
pytest tests/integration_tests/
```

## Configuration

The system is highly configurable through the `.env` file and the Configuration
class. Key configuration options include:

- **LLM Selection**: Choose between different language models
- **Search Providers**: Configure multiple search engine integrations
- **Content Filters**: Set uniqueness thresholds and relevance criteria
- **Publishing Workflow**: Customize Ghost CMS publishing parameters

## API Documentation

The FastAPI backend provides comprehensive API documentation available at:
http://localhost:8000/docs

Key endpoints include:

- `/search`: Content search and curation
- `/generate`: Article generation
- `/publish`: Ghost CMS publishing
- `/notify`: Slack notifications

## Contributing

We welcome contributions! Please see our
[Contribution Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file
for details.
