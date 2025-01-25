import pytest
from ghostwriter.utils.unique.lightrag_ui import LightRAG, QueryParam
from ghostwriter.utils.publish.ghost import GhostContentAPI
from unittest.mock import Mock

@pytest.fixture
def mock_ghost_api():
    api = Mock(spec=GhostContentAPI)
    api.get_posts.return_value = [
        {
            "id": "1",
            "title": "Test Article",
            "html": "<p>Test content</p>",
            "authors": [{"name": "Author 1"}],
            "tags": [{"name": "tag1"}]
        }
    ]
    return api

def test_lightrag_ghost_integration(mock_ghost_api):
    # Mock LLM and embedding functions
    def mock_llm(prompt, **kwargs):
        return "Mock response"
        
    def mock_embed(texts):
        return np.zeros((len(texts), 1024))
    
    rag = LightRAG(
        working_dir="./test_data",
        llm_model_func=mock_llm,
        embedding_func=EmbeddingFunc(1024, 512, mock_embed),
        ghost_api=mock_ghost_api
    )
    
    # Test loading articles
    num_articles = rag.load_ghost_articles()
    assert num_articles == 1
    
    # Test querying
    result = rag.query("Test query", QueryParam(mode="naive"))
    assert "Test query" in result
    
    # Test content storage
    assert len(rag.knowledge_graph) == 1
    stored_content = list(rag.knowledge_graph.values())[0]
    assert "Test Article" in stored_content['content']
    assert stored_content['metadata']['id'] == "1"
