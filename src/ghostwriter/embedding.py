import os
import logging
import requests
from .configuration import Configuration

async def generate_embeddings(text, configuration: Configuration):
    """Generates vector embeddings using Pinecone or OpenAI-compatible API."""

    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_URL = os.getenv("PINECONE_URL")

    HEADERS = {
        "Api-Key": PINECONE_API_KEY,
        "Content-Type": "application/json",
        "X-Pinecone-API-Version": "2024-10"
    }

    payload = {
        "model": configuration.embedding_model,  # Use model from configuration
        "parameters": {"input_type": "passage"}, 
        "inputs": [{"text": text}]
    }
    
    response = requests.post(PINECONE_URL, headers=HEADERS, json=payload)

    if response.status_code == 200:
        return response.json()["data"][0]["values"]
    else:
        logging.error(f"Embedding API Error: {response.text}")
        return None