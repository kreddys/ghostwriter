import logging
import os
import json
import psycopg2
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Pinecone API Key & Endpoint
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_URL = "https://api.pinecone.io/embed"
HEADERS = {
    "Api-Key": PINECONE_API_KEY,
    "Content-Type": "application/json",
    "X-Pinecone-API-Version": "2024-10"
}

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

# Define schema name
SCHEMA_NAME = "ai"

# Create schema if not exists
cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};")

# Ensure the schema is in the search path
cursor.execute(f"SET search_path TO {SCHEMA_NAME}, public;")

# Install required extensions (pgvector)
cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
logging.info("pgvector extension enabled.")

# Create table with vector type for embeddings
cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS "{SCHEMA_NAME}".embeddings (
        id TEXT PRIMARY KEY,
        vector vector(1024),  -- Use pgvector for embeddings
        text TEXT NOT NULL,
        metadata JSONB DEFAULT '{{}}'::JSONB
    );
""")
conn.commit()
logging.info(f"Table '{SCHEMA_NAME}.embeddings' checked/created successfully.")

# Sample dataset with metadata
data = [
    {"id": "vec1", "text": "Apple is a popular fruit known for its sweetness and crisp texture.", "metadata": {"category": "fruit", "source": "general knowledge"}},
    {"id": "vec2", "text": "The tech company Apple is known for its innovative products like the iPhone.", "metadata": {"category": "technology", "source": "business news"}},
    {"id": "vec3", "text": "Many people enjoy eating apples as a healthy snack.", "metadata": {"category": "food", "source": "health magazine"}},
    {"id": "vec4", "text": "Apple Inc. has revolutionized the tech industry with its sleek designs and user-friendly interfaces.", "metadata": {"category": "technology", "source": "tech news"}},
    {"id": "vec5", "text": "An apple a day keeps the doctor away, as the saying goes.", "metadata": {"category": "proverb", "source": "popular sayings"}},
    {"id": "vec6", "text": "Apple Computer Company was founded on April 1, 1976, by Steve Jobs, Steve Wozniak, and Ronald Wayne as a partnership.", "metadata": {"category": "history", "source": "Wikipedia"}}
]

# Generate embeddings using Pinecone API
logging.info("Generating embeddings via Pinecone API...")
payload = {
    "model": "multilingual-e5-large",
    "parameters": {"input_type": "passage", "truncate": "END"},
    "inputs": [{"text": d["text"]} for d in data]
}

response = requests.post(PINECONE_URL, headers=HEADERS, data=json.dumps(payload))

if response.status_code != 200:
    logging.error(f"Failed to fetch embeddings: {response.text}")
    exit(1)

embeddings = response.json()
logging.info("Embeddings generated successfully.")

# Insert embeddings into PostgreSQL
logging.info("Inserting/updating records in PostgreSQL...")
for d, e in zip(data, embeddings["data"]):
    vector_values = e["values"]  # Ensure vector values are correctly formatted

    cursor.execute(f"""
        INSERT INTO {SCHEMA_NAME}.embeddings (id, vector, text, metadata)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE
        SET vector = EXCLUDED.vector, text = EXCLUDED.text, metadata = EXCLUDED.metadata;
    """, (d["id"], vector_values, d["text"], json.dumps(d["metadata"])))

conn.commit()
logging.info("Records inserted/updated in PostgreSQL successfully.")

# Define query
query = "Tell me about the tech company known as Apple."

# Generate embedding for query using Pinecone API
logging.info("Generating embedding for the query...")
query_payload = {
    "model": "multilingual-e5-large",
    "parameters": {"input_type": "query"},
    "inputs": [{"text": query}]
}

query_response = requests.post(PINECONE_URL, headers=HEADERS, data=json.dumps(query_payload))

if query_response.status_code != 200:
    logging.error(f"Failed to fetch query embedding: {query_response.text}")
    exit(1)

query_embedding = query_response.json()["data"][0]["values"]
logging.info("Query embedding generated.")

# Perform similarity search in PostgreSQL using cosine similarity
logging.info("Performing similarity search in PostgreSQL...")
cursor.execute(f"""
    SELECT id, text, metadata, 1 - (vector <#> %s::vector) AS similarity
    FROM {SCHEMA_NAME}.embeddings
    ORDER BY similarity DESC
    LIMIT 3;
""", (query_embedding,))
results = cursor.fetchall()

logging.info("Search completed. Displaying results:")
for row in results:
    logging.info(f"ID: {row[0]}, Text: {row[1]}, Metadata: {row[2]}, Similarity Score: {row[3]}")

# Close PostgreSQL connection
cursor.close()
conn.close()
