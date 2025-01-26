"""Test script for Ghost to LightRAG integration with article tracking"""
import os
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc
from lightrag.llm.openai import openai_complete_if_cache
from pinecone.grpc import PineconeGRPC as Pinecone
from ghostwriter.utils.publish.api import fetch_ghost_articles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def deepseek_llm_func(prompt, **kwargs) -> str:
    return await openai_complete_if_cache(
        "deepseek-chat",
        prompt,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        **kwargs
    )

async def pinecone_embed_func(texts: list[str]) -> list[list[float]]:
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    embeddings = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=texts,
        parameters={"input_type": "passage", "truncate": "END"}
    )
    return [e['values'] for e in embeddings.data]

def load_tracking_data(working_dir: str) -> dict:
    """Load existing article tracking data"""
    tracking_file = Path(working_dir) / "ghost_tracking.json"
    if tracking_file.exists():
        with open(tracking_file, "r") as f:
            return json.load(f)
    return {}

def save_tracking_data(working_dir: str, data: dict):
    """Save article tracking data"""
    tracking_file = Path(working_dir) / "ghost_tracking.json"
    with open(tracking_file, "w") as f:
        json.dump(data, f, indent=2)

def main():
    # Verify required environment variables
    required_vars = {
        "GHOST_APP_URL": os.getenv("GHOST_APP_URL"),
        "GHOST_API_KEY": os.getenv("GHOST_API_KEY"),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
        "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY")
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return

    async def process_articles():
        # Initialize LightRAG
        working_dir = "./lightrag_ghost_data"
        os.makedirs(working_dir, exist_ok=True)
        
        rag = LightRAG(
            working_dir=working_dir,
            llm_model_func=deepseek_llm_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=1024,
                max_token_size=512,
                func=pinecone_embed_func
            )
        )

        # Load tracking data
        tracked_articles = load_tracking_data(working_dir)
        logger.info(f"Loaded tracking data for {len(tracked_articles)} articles")

        # Fetch and process Ghost articles
        try:
            logger.info("Fetching articles from Ghost...")
            articles = await fetch_ghost_articles(
                required_vars["GHOST_APP_URL"],
                required_vars["GHOST_API_KEY"]
            )
            
            if not articles:
                logger.info("No articles found in Ghost")
                return
                
            # Filter out already processed articles
            new_articles = [
                article for article in articles 
                if article.id not in tracked_articles
            ]
            
            if not new_articles:
                logger.info("No new articles to process")
                return
                
            logger.info(f"Processing {len(new_articles)} new articles...")
            
            # Format and store new articles
            article_contents = [
                f"Title: {article.title}\nContent: {article.content}"
                for article in new_articles
            ]
            
            logger.info("Storing new articles in LightRAG...")
            await rag.ainsert(article_contents)
            
            # Update tracking data
            for article in new_articles:
                tracked_articles[article.id] = {
                    "title": article.title,
                    "timestamp": datetime.now().isoformat()
                }
                
            save_tracking_data(working_dir, tracked_articles)
                
            logger.info(f"Successfully stored {len(new_articles)} new articles")
            logger.info(f"Total tracked articles: {len(tracked_articles)}")
            
        except Exception as e:
            logger.error(f"Error processing articles: {str(e)}", exc_info=True)

    # Run the async process
    asyncio.run(process_articles())

if __name__ == "__main__":
    main()
