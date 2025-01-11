"""Tool for checking uniqueness of search results."""
import logging
from typing import Dict, List, Any, Annotated
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, InjectedToolArg
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from ..state import State

logger = logging.getLogger(__name__)

class UniquenessCheckerTool(BaseTool):
    name = "uniqueness_checker"
    description = "Check and filter unique search results"
    vector_store = InMemoryVectorStore(OpenAIEmbeddings())

    def check_result_uniqueness(self, result: Dict, similarity_threshold: float = 0.85) -> bool:
        """Check if a search result is unique."""
        query = f"Title: {result.get('title', '')}\nContent: {result.get('content', '')}"
        similar_docs = self.vector_store.similarity_search_with_score(query, k=1)
        
        if not similar_docs:
            return True
            
        doc, score = similar_docs[0]
        return score <= similarity_threshold

    def add_result(self, result: Dict):
        """Add a search result to memory."""
        document = Document(
            page_content=f"Title: {result.get('title', '')}\nContent: {result.get('content', '')}",
            metadata={
                "url": result.get('url', ''),
                "title": result.get('title', '')
            }
        )
        self.vector_store.add_documents([document])

    async def _arun(
        self,
        state: State,
        config: Annotated[RunnableConfig, InjectedToolArg()],
    ) -> State:
        """
        Filter and return unique search results.
        """
        logger.info("Starting uniqueness check for search results")
        
        unique_results = {}
        
        for source, results in state.search_results.items():
            if not isinstance(results, list):
                continue
                
            source_unique_results = []
            for result in results:
                if self.check_result_uniqueness(result):
                    source_unique_results.append(result)
                    self.add_result(result)
                    logger.info(f"Added unique result from {source}: {result.get('title', '')}")
                else:
                    logger.info(f"Skipped duplicate result from {source}: {result.get('title', '')}")
            
            unique_results[source] = source_unique_results
        
        # Update state with unique results
        state.search_results = unique_results
        return state

    def _run(
        self,
        state: State,
        config: Annotated[RunnableConfig, InjectedToolArg()],
    ) -> State:
        """Synchronous version of the tool (not implemented)."""
        raise NotImplementedError("This tool only supports async execution")