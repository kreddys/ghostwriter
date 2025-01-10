from langchain_ollama import OllamaEmbeddings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ollama_embeddings():
    try:
        # Initialize embeddings with host.docker.internal to access local Ollama instance
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url="http://host.docker.internal:11434"
        )

        # Test with a sample text
        test_text = "The sky is blue because of Rayleigh scattering"
        
        # Try to generate embeddings
        vector = embeddings.embed_query(test_text)
        
        logger.info("Successfully connected to Ollama!")
        logger.info(f"Generated embedding vector (first 5 dimensions): {vector[:5]}")
        return True
        
    except Exception as e:
        logger.error(f"Error connecting to Ollama: {str(e)}")
        return False

if __name__ == "__main__":
    test_ollama_embeddings()