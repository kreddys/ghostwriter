import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
LIGHTRAG_API_URL = "http://localhost:9621"  # Replace with your LightRAG API URL

def query_lightrag(query: str):
    """
    Query LightRAG for relevant information based on the input query.
    """
    try:
        # Make a POST request to the /query endpoint
        logger.info(f"Querying LightRAG for: {query}")
        response = requests.post(
            f"{LIGHTRAG_API_URL}/query",
            json={
                "query": query,
                "mode": "hybrid"  # You can change this to "naive", "local", "global", etc.
            }
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            response_data = response.json()
            if "response" in response_data:
                logger.info("Received a response from LightRAG.")
                return response_data["response"]
            else:
                logger.error("Unexpected response format from LightRAG.")
                return None
        else:
            logger.error(f"Failed to query LightRAG. Response: {response.json()}")
            return None
    
    except Exception as e:
        logger.error(f"Error querying LightRAG: {str(e)}")
        return None

def display_response(response: str):
    """
    Display the query response in a readable format.
    """
    if not response:
        logger.info("No response found.")
        return

    logger.info("Query Response:")
    logger.info("-" * 50)
    logger.info(response)
    logger.info("-" * 50)

if __name__ == "__main__":
    # Example query
    query = "Where is Amaravati?"
    
    # Query LightRAG
    response = query_lightrag(query)
    
    # Display the response
    display_response(response)