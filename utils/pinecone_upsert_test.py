import logging
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize a Pinecone client with your API key
logging.info("Initializing Pinecone client...")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Define a sample dataset where each item has a unique ID and piece of text
data = [
    {"id": "vec1", "text": "Apple is a popular fruit known for its sweetness and crisp texture."},
    {"id": "vec2", "text": "The tech company Apple is known for its innovative products like the iPhone."},
    {"id": "vec3", "text": "Many people enjoy eating apples as a healthy snack."},
    {"id": "vec4", "text": "Apple Inc. has revolutionized the tech industry with its sleek designs and user-friendly interfaces."},
    {"id": "vec5", "text": "An apple a day keeps the doctor away, as the saying goes."},
    {"id": "vec6", "text": "Apple Computer Company was founded on April 1, 1976, by Steve Jobs, Steve Wozniak, and Ronald Wayne as a partnership."}
]

# Convert the text into numerical vectors that Pinecone can index
logging.info("Generating embeddings for the dataset...")
embeddings = pc.inference.embed(
    model="multilingual-e5-large",
    inputs=[d['text'] for d in data],
    parameters={"input_type": "passage", "truncate": "END"}
)
logging.info("Embeddings generated successfully.")

# Target the index where you'll store the vector embeddings
logging.info("Connecting to Pinecone index...")
index = pc.Index("example-index")

# Prepare the records for upsert
logging.info("Preparing records for upsert...")
records = []
for d, e in zip(data, embeddings):
    records.append({
        "id": d['id'],
        "values": e['values'],
        "metadata": {'text': d['text']}
    })
logging.info("Records prepared successfully.")

# Upsert the records into the index
logging.info("Upserting records into Pinecone index...")
index.upsert(
    vectors=records,
    namespace="example-namespace"
)
logging.info("Records upserted successfully.")

# Define your query
query = "Tell me about the tech company known as Apple."

# Convert the query into a numerical vector that Pinecone can search with
logging.info("Generating embedding for the query...")
query_embedding = pc.inference.embed(
    model="multilingual-e5-large",
    inputs=[query],
    parameters={"input_type": "query"}
)
logging.info("Query embedding generated.")

# Search the index for the three most similar vectors
logging.info("Performing similarity search in Pinecone index...")
results = index.query(
    namespace="example-namespace",
    vector=query_embedding[0].values,
    top_k=3,
    include_values=False,
    include_metadata=True
)
logging.info("Search completed. Displaying results:")
logging.info(results)
