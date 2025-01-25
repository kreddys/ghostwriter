import os
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache
from pinecone.grpc import PineconeGRPC as Pinecone
from lightrag.utils import EmbeddingFunc

# Initialize DeepSeek LLM function
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

def query_rag_store(query_text, mode="mix", conversation_history=None):
    """Query the RAG store with different modes and optional conversation history"""
    WORKING_DIR = "./lightrag_ghost_data"
    
    if not os.path.exists(WORKING_DIR):
        os.mkdir(WORKING_DIR)

    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=deepseek_llm_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=1024,
            max_token_size=512,
            func=pinecone_embed_func
        )
    )

    query_param = QueryParam(
        mode=mode,
        conversation_history=conversation_history,
        history_turns=3 if conversation_history else 0
    )

    try:
        return rag.query(query_text, param=query_param)
    except Exception as e:
        print(f"Error querying RAG store: {str(e)}")
        return None

def main():
    
    print("\nHybrid search results:")
    #print(query_rag_store("Is there any article already available about Chandrababu Visitng Davos? Respond with just True or False and few lines of details in a new line after True or False", mode="hybrid"))
    print(query_rag_store("Are there any articles about Nidamarru, Give me the article Id if it exist", mode="hybrid"))

if __name__ == "__main__":
    main()
