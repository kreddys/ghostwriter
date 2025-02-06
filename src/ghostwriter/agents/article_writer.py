import os
import logging
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from ..prompts import ARTICLE_WRITER_PROMPT
from ..state import State
from ..configuration import Configuration
from ghostwriter.utils.publish.api import fetch_ghost_tags
from ..llm import get_llm

logger = logging.getLogger(__name__)

async def article_writer_agent(
    state: State,
    config: RunnableConfig
) -> State:
    """
    Agent that processes unique results and generates articles.
    Generates plain text articles, including title, content, and tags.
    """
    logger.info("=== Starting Article Writer ===")
    
    # Initialize tool state
    if 'article_writer' not in state.tool_states:
        state.tool_states['article_writer'] = {
            'articles': [],
            'generation_successful': False,
            'processed_results': 0,
            'generated_articles': 0,
            'errors': 0
        }
    writer_state = state.tool_states['article_writer']
    
    try:
        # Get unique results from checker tool state
        checker_state = state.tool_states.get('checker', {})
        unique_results = checker_state.get('unique_results', {})

        if not unique_results:
            logger.info("No unique results found - ending workflow")
            writer_state['generation_successful'] = False
            return state

        configuration = Configuration.from_runnable_config(config)
        model = get_llm(configuration, temperature=0.7)

        # Fetch Ghost CMS tags
        app_url = os.getenv("GHOST_APP_URL")
        ghost_api_key = os.getenv("GHOST_API_KEY")

        if not app_url or not ghost_api_key:
            raise ValueError("Ghost API credentials not configured")

        ghost_tags = await fetch_ghost_tags(app_url, ghost_api_key)
        tag_names = [tag.name for tag in ghost_tags]

        articles = []

        # Process each unique result
        for query, results in unique_results.items():
            if not isinstance(results, list):
                continue

            logger.info(f"Processing query: {query}")
            logger.info(f"Results to process: {len(results)}")

            for result in results:
                writer_state['processed_results'] += 1
                url = result.get('url', 'No URL')

                logger.info(f"Generating article from: {url}")

                try:
                    # Generate article title, content, and tags
                    messages = [
                        SystemMessage(
                            content=ARTICLE_WRITER_PROMPT.format(
                                content=result.get('content', 'N/A'),
                                tag_names=tag_names
                            )
                        )
                    ]

                    response = await model.ainvoke(messages)
                    response_text = response.content.strip()

                    # Split the response into lines and clean extra newlines
                    lines = [line.strip() for line in response_text.split("\n") if line.strip()]
                    
                    # Check if there are enough lines to process
                    if len(lines) < 3:
                        raise ValueError("Generated article is too short or missing essential content")

                    # Search for the first and last separator dynamically
                    try:
                        first_separator_idx = lines.index('---')
                        last_separator_idx = len(lines) - 1 - lines[::-1].index('---')

                        # Ensure both separators are found
                        if first_separator_idx >= last_separator_idx:
                            raise ValueError("Invalid article format: separators are in the wrong order")
                    except ValueError:
                        raise ValueError("Article format does not contain valid separators")

                    # Extract title (everything before the first separator)
                    article_title = "\n".join(lines[:first_separator_idx]).strip()

                    # Extract content (everything between the first and last separator)
                    article_content = "\n".join(lines[first_separator_idx + 1:last_separator_idx]).strip()

                    # Extract tags (last line after the second separator)
                    article_tags = [tag.strip() for tag in lines[last_separator_idx + 1].split(",") if tag.strip()]

                    if not article_tags:
                        raise ValueError("No tags found in the AI response")

                    # Store generated article
                    articles.append({
                        'title': article_title,
                        'content': article_content,
                        'source_url': url,
                        'query': query,
                        'tags': article_tags
                    })
                    writer_state['generated_articles'] += 1

                    logger.info("Article generated successfully")

                except Exception as e:
                    writer_state['errors'] += 1
                    logger.error(f"Error generating article: {str(e)}")
                    continue

        # Update state
        writer_state['articles'] = articles
        writer_state['generation_successful'] = True

        logger.info("=== Article Writer Summary ===")
        logger.info(f"Processed results: {writer_state['processed_results']}")
        logger.info(f"Generated articles: {writer_state['generated_articles']}")
        logger.info(f"Errors: {writer_state['errors']}")
        logger.info("=== Article Writer Completed ===")

        return state

    except Exception as e:
        logger.error(f"Article writer failed: {str(e)}")
        writer_state['generation_successful'] = False
        raise
