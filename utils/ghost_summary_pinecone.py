import os
import requests
import jwt
import json
import logging
from datetime import datetime as date
from bs4 import BeautifulSoup
from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment Variables
GHOST_ADMIN_API_KEY = os.getenv("GHOST_ADMIN_API_KEY")
GHOST_API_URL = os.getenv("GHOST_APP_URL") + "/ghost/api/admin/posts/?formats=html,lexical&limit=50&page={}"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "ghost-posts"
PINECONE_NAMESPACE = "ghost-namespace"

# Generate JWT Token for Ghost Admin API
id, secret = GHOST_ADMIN_API_KEY.split(":")
iat = int(date.now().timestamp())
header = {"alg": "HS256", "typ": "JWT", "kid": id}
payload = {"iat": iat, "exp": iat + 5 * 60, "aud": "/admin/"}
token = jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers=header)

# Initialize OpenAI and Pinecone Clients
logging.info("Initializing OpenAI and Pinecone clients...")
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# Function to extract text from HTML
def extract_text_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

# Fetch, process, and store posts
def process_ghost_posts():
    page = 1
    while True:
        url = GHOST_API_URL.format(page)
        headers = {"Authorization": f"Ghost {token}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logging.error(f"Error fetching page {page}: {response.status_code}, {response.text}")
            break
        
        data = response.json()
        posts = data.get("posts", [])
        if not posts:
            logging.info("No more posts found.")
            break
        
        for post in posts:
            post_id = post["id"]
            html_content = post["html"]
            extracted_text = extract_text_from_html(html_content)
            
            logging.info(f"Summarizing post {post_id}...")
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Summarize the given text into 450 words."},
                    {"role": "user", "content": extracted_text},
                ],
                stream=False
            )
            summary = response.choices[0].message.content
            
            logging.info(f"Upserting summarized post {post_id} into Pinecone...")
            embedding = pc.inference.embed(
                model="multilingual-e5-large",
                inputs=[summary],
                parameters={"input_type": "passage", "truncate": "END"}
            )
            
            index.upsert(
                vectors=[
                    {
                        "id": post_id,
                        "values": embedding[0].values,
                        "metadata": {"summary": summary}
                    }
                ],
                namespace=PINECONE_NAMESPACE
            )
        
        logging.info(f"Processed {len(posts)} posts from page {page}")
        page += 1

# Run the process
process_ghost_posts()
