import os
import logging
import asyncpg
from typing import Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from ..state import State
from ..configuration import Configuration
from ..utils.verify.url_filter import filter_existing_urls
from ..utils.verify.relevance_checker import RelevanceChecker
from ..utils.verify.llm_summarizer import summarize_content
from ..embedding import generate_embeddings

logger = logging.getLogger(__name__)

async def check_similarity_with_existing(embedding, similarity_threshold):
    """Check if the embedding is similar to existing embeddings in the database."""
    conn = await asyncpg.connect(
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
    )

    embedding_str = f"[{', '.join(map(str, embedding))}]" 

    query = f"""
    SELECT id, title, url, 1 - (vector <=> $1::vector) AS similarity
    FROM post_embeddings
    WHERE 1 - (vector <=> $1::vector) > {similarity_threshold}
    ORDER BY similarity DESC
    LIMIT 1;
    """
    
    result = await conn.fetchrow(query, embedding_str)

    if result:
        logger.info(f"Similar article found: ID={result['id']}, URL={result['url']}, Similarity={result['similarity']:.4f}")
    else:
        logger.info("No similar articles found. The content is unique.")

    await conn.close()
    return result

async def verifier(
    state: State,
    config: Annotated[RunnableConfig, InjectedToolArg()]
) -> dict:
    """Filter and return only unique and relevant search results."""
    logger.info("=== Starting Relevance & Uniqueness Checker ===")

    if 'verifier' not in state.tool_states:
        state.tool_states['verifier'] = {
            'unique_results': {},
            'check_successful': False,
        }
    verifier_state = state.tool_states['verifier']

    try:
        # Get scraper results
        scraper_state = state.tool_states.get('scraper', {})
        if not scraper_state.get('scrape_successful', False):
            logger.warning("Scraping was not successful")
            verifier_state['check_successful'] = False
            return state

        scraped_results = scraper_state.get('scraped_results', {})
        if not scraped_results:
            logger.warning("No scraped results found")
            verifier_state['check_successful'] = False
            return state

        configuration = Configuration.from_runnable_config(config)
        use_url_filtering = configuration.use_url_filtering
        skip_uniqueness_checker = configuration.skip_uniqueness_checker
        
        # Initialize RelevanceChecker
        relevance_checker = RelevanceChecker(
            topic=configuration.topic,
            threshold=configuration.relevance_similarity_threshold,
            configuration=configuration
        )

        unique_results = {}

        logger.info(f"Processing {len(scraped_results)} queries")

        for query, results in scraped_results.items():
            if not isinstance(results, list):
                continue

            logger.info(f"\nProcessing query: {query}")
            logger.info(f"Results to process: {len(results)}")

            filtered_results = filter_existing_urls(results) if use_url_filtering else results

            source_unique_results = []

            for result in filtered_results:
                if result.get('scrape_status') != 'success':
                    logger.info(f"✗ Skipped URL (scrape_status not success): {result['url']}")
                    continue

                # Summarize content
                summary = await summarize_content(result['content'], configuration)
                if not summary:
                    logger.warning(f"Failed to summarize content for: {result['url']}")
                    continue
                logger.info(f"Summarized content: {summary[:200]}...")  # Log first 200 chars

                # Check relevance
                is_relevant = await relevance_checker.is_relevant(summary)
                if not is_relevant:
                    logger.info(f"✗ Rejected URL (not relevant): {result['url']}")
                    continue
                logger.info(f"✓ Relevant URL:: {result['url']}")

                # Generate embeddings
                embedding = await generate_embeddings(summary)
                if not embedding:
                    logger.warning(f"Failed to generate embeddings for: {result['url']}")
                    continue
                logger.info(f"✓ Embeddings generated for URL:: {result['url']}")

                # Skip uniqueness check if the flag is set
                if not skip_uniqueness_checker:
                    # Check for similar content
                    similar_article = await check_similarity_with_existing(embedding, configuration.similarity_threshold)

                    if not similar_article:
                        source_unique_results.append(result)
                        logger.info(f"✓ Unique URL: {result['url']}")
                    else:
                        logger.info(f"✗ Non-unique (similar to {similar_article['url']}): {result['url']}")
                else:
                    logger.info(f"Skipping uniqueness check for URL: {result['url']}")
                    source_unique_results.append(result)

            if source_unique_results:
                unique_results[query] = source_unique_results

            verifier_state['unique_results'] = unique_results
            verifier_state['check_successful'] = bool(unique_results)

        logger.info("\n=== Final Unique Results Summary ===")
        logger.info(f"Total unique results: {sum(len(results) for results in unique_results.values())}")

        return state

    except Exception as e:
        logger.error(f"Error in uniqueness and relevance checker: {str(e)}")
        return state
