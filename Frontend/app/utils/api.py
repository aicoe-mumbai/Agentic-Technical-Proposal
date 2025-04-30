import requests
import json
import streamlit as st
from typing import Dict, List, Optional, Any, Union
import time

from Frontend.app.config import API_BASE_URL, API_V1_PATH

class ApiClient:
    """API client for interacting with the backend"""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        self.api_path = API_V1_PATH
    
    def _get_url(self, endpoint: str) -> str:
        """Get the full URL for an endpoint"""
        return f"{self.base_url}{self.api_path}{endpoint}"
    
    def get_templates(self) -> Dict[str, Dict[str, str]]:
        """Get all templates"""
        try:
            response = requests.get(self._get_url("/templates/"))
            response.raise_for_status()
            return response.json().get("templates", {})
        except Exception as e:
            st.error(f"Error fetching templates: {str(e)}")
            return {}
    
    def get_template(self, project_name: str) -> Dict[str, Any]:
        """Get a specific template by name"""
        try:
            response = requests.get(self._get_url(f"/templates/{project_name}"))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching template {project_name}: {str(e)}")
            return {}
    
    def get_template_data(self, project_name: str) -> Dict[str, str]:
        """Get template data (Excel key-value pairs)"""
        try:
            response = requests.get(self._get_url(f"/templates/{project_name}/data"))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching template data for {project_name}: {str(e)}")
            return {}
    
    def create_template(self, project_name: str, project_TOC: str, excel_file=None) -> Dict[str, Any]:
        """Create a new template"""
        try:
            data = {"project_name": project_name, "project_TOC": project_TOC}
            files = {}
            if excel_file:
                files = {"excel_file": excel_file}
            
            response = requests.post(self._get_url("/templates/"), data=data, files=files)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error creating template: {str(e)}")
            return {}
    
    def upload_document(self, file) -> Dict[str, Any]:
        """Upload a document"""
        try:
            files = {"file": file}
            response = requests.post(self._get_url("/documents/upload"), files=files)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error uploading document: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def check_document_status(self, filename: str) -> Dict[str, Any]:
        """Check document processing status"""
        try:
            response = requests.get(self._get_url(f"/documents/{filename}/status"))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error checking document status: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def extract_document_scope(self, filename: str, cache: bool = True) -> Dict[str, Any]:
        """Extract scope from document"""
        try:
            url = self._get_url(f"/documents/{filename}/scope")
            if not cache:
                # Add a timestamp parameter to bypass any caching
                url += f"?cache=false&t={int(time.time())}"
                
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error extracting document scope: {str(e)}")
            return {"is_complete": False, "message": str(e)}
    
    def confirm_document_scope(self, filename: str, page_numbers: List[int]) -> Dict[str, Any]:
        """Confirm document scope with user-selected pages"""
        try:
            data = {"page_numbers": page_numbers}
            response = requests.post(
                self._get_url(f"/documents/{filename}/confirm-scope"),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error confirming document scope: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def generate_topics(self, document_name: str, template_name: str) -> Dict[str, Any]:
        """Generate topics based on document and template"""
        try:
            response = requests.post(
                self._get_url(f"/analysis/generate-topics/{document_name}/{template_name}")
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error generating topics: {str(e)}")
            return {"topics": [], "raw_response": str(e)}
    
    def get_document_topics(self, document_name: str, template_name: str) -> Dict[str, Any]:
        """Get previously generated topics for a document and template"""
        try:
            response = requests.get(
                self._get_url(f"/documents/{document_name}/topics/{template_name}")
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error retrieving document topics: {str(e)}")
            return {"topics": []}
    
    def save_document_topics(self, document_name: str, template_name: str, topics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Save generated topics for a document and template"""
        try:
            data = {"topics": topics}
            response = requests.post(
                self._get_url(f"/documents/{document_name}/topics/{template_name}"),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error saving document topics: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def generate_content(self, document_name: str, template_name: str, topic: str) -> Dict[str, Any]:
        """Generate content for a topic"""
        try:
            data = {"topic": topic}
            response = requests.post(
                self._get_url(f"/analysis/generate-content/{document_name}/{template_name}"),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error generating content: {str(e)}")
            return {"content": f"Error: {str(e)}", "topic": topic}
    
    def save_document_content(self, document_name: str, topic_id: int, content: str) -> Dict[str, Any]:
        """Save content for a document topic"""
        try:
            data = {"topic_id": topic_id, "content": content}
            response = requests.post(
                self._get_url(f"/documents/{document_name}/content"),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error saving document content: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def save_document_content_bulk(self, document_name: str, content_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Save content for multiple document topics at once"""
        try:
            response = requests.post(
                self._get_url(f"/documents/{document_name}/content/bulk"),
                json=content_items
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error saving bulk document content: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_document_content(self, document_name: str, topic_id: int) -> Dict[str, Any]:
        """Get content for a document topic"""
        try:
            response = requests.get(
                self._get_url(f"/documents/{document_name}/content/{topic_id}")
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error retrieving document content: {str(e)}")
            return {"content": "", "exists": False}
    
    def chat_with_document(
        self, document_name: str, template_name: str, message: str, history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Chat with the document"""
        try:
            data = {"message": message, "history": history}
            response = requests.post(
                self._get_url(f"/analysis/chat/{document_name}/{template_name}"),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error in chat: {str(e)}")
            return {"response": f"Error: {str(e)}", "status": "error"}
    
    def extract_page_text(self, filename: str, page_range: str) -> Dict[str, Any]:
        """Extract text from specific pages"""
        try:
            response = requests.get(self._get_url(f"/documents/{filename}/page/{page_range}"))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error extracting page text: {str(e)}")
            return {"text": f"Error: {str(e)}"}
    
    def query_document(self, filename: str, query: str) -> Dict[str, Any]:
        """Query the document"""
        try:
            data = {"query": query}
            response = requests.post(
                self._get_url(f"/documents/{filename}/query"),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error querying document: {str(e)}")
            return {"result": f"Error: {str(e)}"}
    
    def range_query_document(
        self, filename: str, query: str, start_idx: int = 0, end_idx: int = 3
    ) -> Dict[str, Any]:
        """Query the document with custom result range"""
        try:
            data = {"query": query, "start_idx": start_idx, "end_idx": end_idx}
            response = requests.post(
                self._get_url(f"/documents/{filename}/range-query"),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error in range query: {str(e)}")
            return {"result": f"Error: {str(e)}"}

    def delete_template(self, project_name: str) -> bool:
        """Delete a template by name"""
        try:
            response = requests.delete(self._get_url(f"/templates/{project_name}"))
            response.raise_for_status()
            return True
        except Exception as e:
            st.error(f"Error deleting template: {str(e)}")
            return False

# Create a singleton instance
api_client = ApiClient()