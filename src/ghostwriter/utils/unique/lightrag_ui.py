"""Streamlit UI components for LightRAG document management."""
import os
import streamlit as st
import subprocess
from pathlib import Path

class LightRAGUI:
    def __init__(self):
        self.working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_data")
        self.cli_path = str(Path(__file__).parent / "lightrag_cli.py")
        self.rag = None

    async def initialize(self):
        """Initialize the LightRAG instance"""
        return True

    def _run_cli_command(self, command: str):
        """Run a CLI command and return the output"""
        try:
            result = subprocess.run(
                ["python", self.cli_path, command],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                st.error(f"Command failed: {result.stderr}")
                return False
            return result.stdout
        except Exception as e:
            st.error(f"Error running command: {str(e)}")
            return False

    def sync_ghost_articles(self):
        """Sync Ghost articles to LightRAG using CLI"""
        with st.spinner("Syncing Ghost articles..."):
            result = self._run_cli_command("sync-ghost")
            if result:
                st.success("Successfully synced Ghost articles")
                return True
            return False

    def check_duplicate_content(self, content: str) -> bool:
        """
        Check if content already exists in the knowledge store.
        """
        # Save content to temp file
        temp_path = Path(self.working_dir) / "temp_content.txt"
        try:
            with open(temp_path, "w") as f:
                f.write(content)
            
            # Run CLI command to check duplicates
            result = self._run_cli_command(f"check-duplicate --file {temp_path}")
            if result and "Duplicate content found" in result:
                return True
            return False
        except Exception as e:
            st.error(f"Error checking duplicates: {str(e)}")
            return False
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def show_management_interface(self):
        """Show LightRAG document management interface"""
        st.title("LightRAG Knowledge Store")
        
        # Check new content
        with st.expander("Check for Duplicate Content"):
            new_content = st.text_area("Paste new content to check for duplicates")
            if st.button("Check for Duplicates"):
                if new_content:
                    with st.spinner("Checking for duplicates..."):
                        is_duplicate = self.check_duplicate_content(new_content)
                        if is_duplicate:
                            st.error("Duplicate content found!")
                        else:
                            st.success("No duplicates found - content is unique")
                else:
                    st.warning("Please enter some content to check")
        
        # Sync Ghost articles
        with st.expander("Sync Ghost Articles"):
            if st.button("Sync Ghost Articles"):
                if self.sync_ghost_articles():
                    st.success("Ghost articles synced successfully")
                else:
                    st.error("Failed to sync Ghost articles")
                
        # View stored documents
        with st.expander("View Stored Documents"):
            if st.button("Refresh Document List"):
                result = self._run_cli_command("list-documents")
                if result:
                    st.write("Stored Documents:")
                    st.code(result)
                else:
                    st.info("No documents found")
