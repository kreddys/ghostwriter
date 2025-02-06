import os
import logging
from getpass import getpass
from langchain_pinecone import PineconeEmbeddings
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from uuid import uuid4
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up Pinecone API key
if not os.getenv("PINECONE_API_KEY"):
    os.environ["PINECONE_API_KEY"] = getpass("Enter your Pinecone API key: ")

# Initialize Pinecone client
logging.info("Initializing Pinecone client...")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Initialize Pinecone embeddings
logging.info("Initializing Pinecone embeddings...")
embeddings = PineconeEmbeddings(model="multilingual-e5-large")

# Check if the index exists, create if not
index_name = "example-index-2"
existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

if index_name not in existing_indexes:
    logging.info(f"Index {index_name} does not exist. Creating a new index...")
    pc.create_index(
        name=index_name,
        dimension=1024,  # Update based on the model's output dimension
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    while not pc.describe_index(index_name).status["ready"]:
        time.sleep(1)
    logging.info(f"Index {index_name} created successfully.")
else:
    logging.info(f"Index {index_name} already exists.")

# Connect to the index
index = pc.Index(index_name)

# Create Pinecone vector store
vector_store = PineconeVectorStore(index=index, embedding=embeddings)

# Define a sample dataset of documents
docs = [
    "Apple is a popular fruit known for its sweetness and crisp texture.",
    "The tech company Apple is known for its innovative products like the iPhone.",
    "Many people enjoy eating apples as a healthy snack.",
    "Apple Inc. has revolutionized the tech industry with its sleek designs and user-friendly interfaces.",
    "An apple a day keeps the doctor away, as the saying goes."
]

# Generate embeddings for the documents
logging.info("Generating embeddings for the documents...")
doc_embeds = embeddings.embed_documents(docs)

# Create documents for the vector store
documents = [Document(page_content=doc, metadata={"id": str(uuid4())}) for doc in docs]

# Add documents to the vector store
logging.info("Adding documents to Pinecone VectorStore...")
vector_store.add_documents(documents=documents, ids=[str(uuid4()) for _ in range(len(documents))])
logging.info("Documents added successfully.")

# Define a query to search for
query = "Tell me about the tech company known as Apple"

# Generate embedding for the query
logging.info("Generating embedding for the query...")
query_embed = embeddings.embed_query(query)

# Perform similarity search
logging.info("Performing similarity search...")
results = vector_store.similarity_search(query, k=3)
logging.info("Search results:")
for res in results:
    logging.info(f"* {res.page_content} [{res.metadata}]")
