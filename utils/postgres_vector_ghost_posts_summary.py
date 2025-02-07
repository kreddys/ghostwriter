import os
import requests
import json
import psycopg2
import logging
import jwt
from bs4 import BeautifulSoup
from openai import OpenAI
from datetime import datetime as date

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Environment Variables
GHOST_ADMIN_API_KEY = os.getenv("GHOST_ADMIN_API_KEY")
GHOST_API_URL = os.getenv("GHOST_APP_URL") + "/ghost/api/admin/posts/?formats=html,lexical&limit=50&page={}"
PG_HOST = os.getenv("POSTGRES_HOST")
PG_DB = os.getenv("POSTGRES_DB")
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
PG_PORT = os.getenv("POSTGRES_PORT")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")  # Example: Ollama, LM Studio
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # API Key (if needed)
MODEL_NAME = os.getenv("OPENAI_MODEL")

# Generate Ghost Admin API Token
id, secret = GHOST_ADMIN_API_KEY.split(":")
iat = int(date.now().timestamp())
token = jwt.encode(
    {"iat": iat, "exp": iat + 5 * 60, "aud": "/admin/"},
    bytes.fromhex(secret),
    algorithm="HS256",
    headers={"alg": "HS256", "typ": "JWT", "kid": id},
)

# PostgreSQL Connection
conn = psycopg2.connect(
    dbname=PG_DB, user=PG_USER, password=PG_PASSWORD, host=PG_HOST, port=PG_PORT
)
cursor = conn.cursor()

# Ensure schema and table exist
SCHEMA_NAME = "public"
cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};")
cursor.execute(f"SET search_path TO {SCHEMA_NAME}, public;")
cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS "{SCHEMA_NAME}".post_embeddings (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        published_at TIMESTAMP,
        url TEXT NOT NULL,
        summary TEXT NOT NULL,
        vector vector(1024),
        metadata JSONB DEFAULT '{{}}'::JSONB,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
""")
conn.commit()

# OpenAI Client for Summarization
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)


def extract_text_from_html(html):
    """Extracts clean text from HTML content."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def summarize_text(text):
    """Summarizes text using an LLM model."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are an expert summarizer. Summarize the given text in 450 words."},
            {"role": "user", "content": text},
        ],
        stream=False
    )
    return response.choices[0].message.content.strip()


def generate_embeddings(text):
    """Generates vector embeddings using Pinecone or OpenAI-compatible API."""
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_URL = "https://api.pinecone.io/embed"
    HEADERS = {
        "Api-Key": PINECONE_API_KEY,
        "Content-Type": "application/json",
        "X-Pinecone-API-Version": "2024-10"
    }

    payload = {"model": "multilingual-e5-large", "parameters": {"input_type": "passage"}, "inputs": [{"text": text}]}
    response = requests.post(PINECONE_URL, headers=HEADERS, json=payload)

    if response.status_code == 200:
        return response.json()["data"][0]["values"]
    else:
        logging.error(f"Embedding API Error: {response.text}")
        return None


def fetch_and_store_posts(post_ids=None, skip_html_extraction=False):
    """Fetches posts from Ghost, summarizes, converts to embeddings, and stores them in PostgreSQL.
    
    Args:
        post_ids (list, optional): List of specific post IDs to update. If None, fetch all.
        skip_html_extraction (bool): If True, use the existing summary instead of extracting text from HTML.
    """
    headers = {"Authorization": f"Ghost {token}"}
    
    if post_ids:
        # Fetch specific posts
        url = f"{os.getenv('GHOST_APP_URL')}/ghost/api/admin/posts/?formats=html,lexical&filter=id:[{','.join(post_ids)}]"
        response = requests.get(url, headers=headers)
    else:
        # Fetch all posts
        url = GHOST_API_URL.format(1)
        response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Error fetching posts: {response.status_code}")
        return

    posts = response.json().get("posts", [])
    if not posts:
        logging.info("No posts found.")
        return

    for post in posts:
        post_id = post["id"]
        title = post.get("title", "Untitled")
        published_at = post.get("published_at", None)
        url = post.get("url", "#")
        html_content = post.get("html", "")
        existing_summary = post.get("excerpt", "")

        if skip_html_extraction:
            # Use existing summary if available
            summarized_text = existing_summary or "No summary available."
        else:
            if not html_content:
                logging.warning(f"Skipping post {post_id} (No HTML content)")
                continue
            extracted_text = extract_text_from_html(html_content)
            summarized_text = summarize_text(extracted_text)

        embedding_vector = generate_embeddings(summarized_text)

        if embedding_vector:
            cursor.execute(f"""
                INSERT INTO {SCHEMA_NAME}.post_embeddings (id, title, published_at, url, summary, vector, metadata, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE
                SET title = EXCLUDED.title,
                    published_at = EXCLUDED.published_at,
                    url = EXCLUDED.url,
                    summary = EXCLUDED.summary,
                    vector = EXCLUDED.vector,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW();
            """, (post_id, title, published_at, url, summarized_text, embedding_vector, json.dumps({"source": "Ghost"})))
            conn.commit()
            logging.info(f"Stored post {post_id} in database.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch and store Ghost posts into the database.")
    parser.add_argument("--ids", nargs="+", help="List of specific post IDs to update")
    parser.add_argument("--skip-html-extraction", action="store_true", help="Skip HTML to text extraction and use the existing summary")

    args = parser.parse_args()

    fetch_and_store_posts(post_ids=args.ids, skip_html_extraction=args.skip_html_extraction)

    cursor.close()
    conn.close()
    logging.info("Process completed successfully.")
