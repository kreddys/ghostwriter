import os
import requests
import jwt
import json
import logging
import psycopg2
from datetime import datetime as date

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
GHOST_ADMIN_API_KEY = os.getenv("GHOST_ADMIN_API_KEY")
GHOST_API_URL = os.getenv("GHOST_APP_URL") + "/ghost/api/admin/posts/?formats=html,lexical&limit=50&page={}"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_URL = os.getenv("PINECONE_URL")
SCHEMA_NAME = "public"

# PostgreSQL Connection
logging.info("Connecting to PostgreSQL database...")
conn = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT")
)
cursor = conn.cursor()

# Create Schema & Table for Embeddings
cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};")
cursor.execute(f"SET search_path TO {SCHEMA_NAME}, public;")
cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS "{SCHEMA_NAME}".post_embeddings (
        id TEXT PRIMARY KEY,
        vector vector(1024),  -- Using pgvector for embeddings
        text TEXT NOT NULL,
        metadata JSONB DEFAULT '{{}}'::JSONB
    );
""")
conn.commit()
logging.info("Database schema and table setup completed.")

# Generate JWT Token for Ghost API
id, secret = GHOST_ADMIN_API_KEY.split(":")
iat = int(date.now().timestamp())
header = {"alg": "HS256", "typ": "JWT", "kid": id}
payload = {"iat": iat, "exp": iat + 5 * 60, "aud": "/admin/"}
token = jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers=header)

# Fetch Posts & Store in PostgreSQL
page = 1
while True:
    url = GHOST_API_URL.format(page)
    headers = {"Authorization": f"Ghost {token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Error fetching page {page}: {response.status_code}, {response.text}")
        break

    posts = response.json().get("posts", [])
    if not posts:
        logging.info("No more posts found.")
        break

    # Process each post
    for post in posts:
        post_id = post["id"]
        title = post["title"]
        html_content = post["html"]
        url = post["url"]

        if not html_content:
            logging.warning(f"Skipping post {post_id} - No HTML content found.")
            continue

        # Generate Embeddings using Pinecone API
        payload = {
            "model": "multilingual-e5-large",
            "parameters": {"input_type": "passage", "truncate": "END"},
            "inputs": [{"text": html_content}]
        }
        response = requests.post(PINECONE_URL, headers={
            "Api-Key": PINECONE_API_KEY,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": "2024-10"
        }, data=json.dumps(payload))

        if response.status_code != 200:
            logging.error(f"Failed to fetch embeddings for post {post_id}: {response.text}")
            continue

        vector_values = response.json()["data"][0]["values"]

        # Insert into PostgreSQL
        cursor.execute(f"""
            INSERT INTO {SCHEMA_NAME}.post_embeddings (id, vector, text, metadata)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET vector = EXCLUDED.vector, text = EXCLUDED.text, metadata = EXCLUDED.metadata;
        """, (post_id, vector_values, html_content, json.dumps({"title": title, "url": url})))

        logging.info(f"Inserted post {post_id} into PostgreSQL.")

    conn.commit()
    page += 1

# Close PostgreSQL connection
cursor.close()
conn.close()
logging.info("All posts processed and inserted into PostgreSQL.")
