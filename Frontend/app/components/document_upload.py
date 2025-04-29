import streamlit as st
import time
from typing import Optional, Dict, Any

from Frontend.app.utils.api import api_client

def render_document_upload() -> Optional[Dict[str, Any]]:
    """
    Render the document upload section
    
    Returns:
        Dictionary with document info if uploaded successfully, None otherwise
    """
    st.header("Upload Document")
    
    uploaded_pdf = st.file_uploader("Upload the SOTR PDF file", type=["pdf"])
    
    if uploaded_pdf is not None:
        # Check if this document has already been processed
        filename = uploaded_pdf.name
        status_result = api_client.check_document_status(filename)
        
        # Document exists and is already processed
        if status_result.get("status") == "processed":
            st.success(f"Document '{filename}' was previously processed!")
            
            # Restore document info to session state
            document_info = {
                "filename": filename,
                "status": "processed",
                "pages": status_result.get("pages", 0)
            }
            st.session_state.document_info = document_info
            
            # Check for previously extracted scope
            scope_result = api_client.extract_document_scope(filename)
            if scope_result and scope_result.get("is_complete", False):
                st.session_state.scope_data = scope_result
                if scope_result.get("is_confirmed", False):
                    st.session_state.scope_confirmed = True
                    st.success("Previously extracted scope retrieved!")
            
            return document_info
            
        # Document needs processing
        if st.button("Process Document"):
            with st.spinner("Uploading document..."):
                result = api_client.upload_document(uploaded_pdf)
                
                if not result.get("success"):
                    error_msg = result.get("message", "Unknown error")
                    if "Tesseract OCR is not installed" in error_msg:
                        st.error("Tesseract OCR is required but not installed. Please install it using:")
                        st.code("sudo apt-get install tesseract-ocr", language="bash")
                        return None
                    else:
                        st.error(f"Error uploading document: {error_msg}")
                        return None
                
                st.success("Document uploaded successfully!")
                
                # Check processing status
                filename = result.get("filename")
                
                progress_text = st.empty()
                progress_bar = st.progress(0)
                
                with st.spinner(""):  # Empty spinner to prevent double spinners
                    max_wait = 300  # Maximum wait time in seconds
                    start_time = time.time()
                    status = "processing"
                    
                    while status == "processing" and (time.time() - start_time) < max_wait:
                        status_result = api_client.check_document_status(filename)
                        status = status_result.get("status", "error")
                        message = status_result.get("message", "")
                        progress = status_result.get("progress", 0)
                        
                        # Update progress text and bar
                        progress_text.text(message)
                        if progress > 0:
                            progress_bar.progress(progress / 100)
                        elif "vector database" in message.lower():
                            progress_bar.progress(0.9)  # 90% for vector DB initialization
                        
                        if status == "processed":
                            progress_bar.progress(1.0)  # 100%
                            progress_text.text("Document processed successfully!")
                            st.success("Document processed successfully!")
                            
                            # Store document info in session state
                            if "document_info" not in st.session_state:
                                st.session_state.document_info = {}
                            
                            st.session_state.document_info = {
                                "filename": filename,
                                "status": "processed",
                                "pages": status_result.get("pages", 0)
                            }
                            
                            return st.session_state.document_info
                        
                        elif status == "error":
                            progress_bar.empty()
                            progress_text.empty()
                            st.error(f"Error processing document: {status_result.get('message', 'Unknown error')}")
                            return None
                        
                        # Wait a bit before checking again
                        time.sleep(2)  # Reduced wait time to make progress updates more frequent
                    
                    if status == "processing":
                        progress_bar.empty()
                        progress_text.empty()
                        st.warning("Document processing is taking longer than expected. Please check back later.")
                        return None
    
    # Return document info from session state if available
    return st.session_state.get("document_info")