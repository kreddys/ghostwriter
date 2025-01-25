"""CLI interface for LightRAG operations."""
import os
import numpy as np
import asyncio
import click
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create file handler
file_handler = logging.FileHandler('lightrag_cli.log')
file_handler.setFormatter(formatter)

# Create stream handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Prevent duplicate logs in Streamlit
logger.propagate = False
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from lightrag.llm.openai import openai_complete_if_cache
from pinecone.grpc import PineconeGRPC as Pinecone
from ghostwriter.utils.publish.api import fetch_ghost_articles

async def deepseek_llm_func(
    prompt, 
    system_prompt=None, 
    history_messages=[], 
    keyword_extraction=False, 
    **kwargs
) -> str:
    return await openai_complete_if_cache(
        "deepseek-chat",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        **kwargs
    )

async def pinecone_embed_func(texts: list[str]) -> np.ndarray:
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    embeddings = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=texts,
        parameters={"input_type": "passage", "truncate": "END"}
    )
    return np.array([e['values'] for e in embeddings.data])

class LightRAGCLI:
    def __init__(self):
        self.working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_data")
        self.rag = None
        
    async def initialize(self):
        if self.rag is None:
            self.rag = LightRAG(
                working_dir=self.working_dir,
                llm_model_func=deepseek_llm_func,
                embedding_func=EmbeddingFunc(
                    embedding_dim=1024,
                    max_token_size=512,
                    func=pinecone_embed_func
                )
            )
        return self.rag

    async def sync_ghost_articles(self):
        required_env_vars = {
            "GHOST_APP_URL": os.getenv("GHOST_APP_URL"),
            "GHOST_API_KEY": os.getenv("GHOST_API_KEY"),
            "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
            "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY")
        }
        
        missing_vars = [var for var, value in required_env_vars.items() if not value]
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
            
        ghost_url = required_env_vars["GHOST_APP_URL"]
        ghost_api_key = required_env_vars["GHOST_API_KEY"]
            
        logger.info("Fetching Ghost articles...")
        try:
            articles = await fetch_ghost_articles(ghost_url, ghost_api_key)
            if not articles:
                logger.error("No articles found in Ghost")
                return False
                
            article_contents = []
            for article in articles:
                content = f"Title: {article.title}\nContent: {article.content}"
                article_contents.append(content)
                
            logger.info(f"Processing {len(articles)} articles")
            logger.info("Storing articles in LightRAG...")
            try:
                await self.rag.insert(article_contents)
                logger.info(f"Successfully stored {len(articles)} articles in LightRAG")
                return True
            except Exception as e:
                logger.error(f"Error storing articles: {str(e)}", exc_info=True)
                return False
        except Exception as e:
            logger.error(f"Error fetching articles: {str(e)}", exc_info=True)
            return False

@click.group()
def cli():
    """LightRAG CLI Interface"""
    pass

@cli.command()
def sync_ghost():
    """Sync Ghost articles to LightRAG"""
    cli = LightRAGCLI()
    asyncio.run(cli.initialize())
    asyncio.run(cli.sync_ghost_articles())

if __name__ == "__main__":
    cli()
