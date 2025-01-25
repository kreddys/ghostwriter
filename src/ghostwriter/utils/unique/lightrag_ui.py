"""Streamlit UI components for LightRAG document management."""
import os
import streamlit as st
import asyncio
from lightrag import LightRAG
from ghostwriter.utils.publish.api import fetch_ghost_articles

class LightRAGUI:
    def __init__(self):
        self.working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_data")
        self.rag = None
        
    async def initialize(self):
        """Initialize LightRAG instance"""
        if self.rag is None:
            self.rag = LightRAG(
                working_dir=self.working_dir,
                log_level="INFO",
                embedding_func=EmbeddingFunc(
                    embedding_dim=1536,
                    max_token_size=8192,
                    func="openai_embed"
                ),
                addon_params={
                    "insert_batch_size": 20,
                    "entity_types": ["organization", "person", "location", "event"]
                }
            )
        return self.rag

    async def sync_ghost_articles(self):
        """Sync Ghost articles to LightRAG"""
        ghost_url = os.getenv("GHOST_APP_URL")
        ghost_api_key = os.getenv("GHOST_API_KEY")
        
        if not all([ghost_url, ghost_api_key]):
            st.error("Ghost credentials not configured")
            return False
            
        with st.spinner("Fetching Ghost articles..."):
            articles = await fetch_ghost_articles(ghost_url, ghost_api_key)
            if not articles:
                st.error("No articles found in Ghost")
                return False
                
            article_contents = []
            for article in articles:
                content = f"Title: {article.title}\nContent: {article.content}"
                article_contents.append(content)
                
            with st.spinner("Storing articles in LightRAG..."):
                self.rag.insert(article_contents)
                st.success(f"Successfully stored {len(articles)} articles in LightRAG")
                return True

    def show_upload_interface(self):
        """Show document upload interface"""
        with st.expander("Upload Documents"):
            uploaded_files = st.file_uploader(
                "Upload documents (PDF, DOCX, TXT)",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True
            )
            
            if uploaded_files:
                with st.spinner("Processing documents..."):
                    try:
                        documents = []
                        for file in uploaded_files:
                            if file.type == "application/pdf":
                                import PyPDF2
                                reader = PyPDF2.PdfReader(file)
                                text = "\n".join([page.extract_text() for page in reader.pages])
                            elif file.type == "text/plain":
                                text = file.read().decode("utf-8")
                            else:
                                # Handle DOCX files
                                from docx import Document
                                doc = Document(file)
                                text = "\n".join([para.text for para in doc.paragraphs])
                                
                            documents.append(text)
                        
                        self.rag.insert(documents)
                        st.success(f"Successfully stored {len(documents)} documents")
                        return True
                    except Exception as e:
                        st.error(f"Error processing documents: {str(e)}")
                        return False
        return None

    def show_management_interface(self):
        """Show LightRAG document management interface"""
        st.title("LightRAG Knowledge Store")
        
        # Initialize LightRAG if not already initialized
        if self.rag is None:
            st.warning("LightRAG not initialized")
            return
            
        # Sync Ghost articles
        with st.expander("Sync Ghost Articles"):
            if st.button("Sync Ghost Articles"):
                asyncio.run(self.sync_ghost_articles())
                
        # Upload custom documents
        self.show_upload_interface()
        
        # View stored documents
        with st.expander("View Stored Documents"):
            if st.button("Refresh Document List"):
                # TODO: Implement document listing functionality
                st.info("Document listing functionality coming soon")
