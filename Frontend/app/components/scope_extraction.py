import streamlit as st
from typing import Dict, Any, Optional, List

from Frontend.app.utils.api import api_client

def render_scope_extraction(document_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Render the scope extraction and confirmation section"""
    st.header("Extract Document Scope")
    
    filename = document_info.get("filename")
    
    if not filename:
        st.error("No document selected")
        return None
    
    if "scope_data" not in st.session_state:
        st.session_state.scope_data = None
    
    if "scope_confirmed" not in st.session_state:
        st.session_state.scope_confirmed = False
    
    if st.button("Extract Scope"):
        with st.spinner("Extracting scope from document..."):
            scope_data = api_client.extract_document_scope(filename)
            
            if scope_data.get("is_complete"):
                st.session_state.scope_data = scope_data
                st.success("Scope extracted successfully!")
            else:
                st.warning("Could not find a clear scope section. Please select pages manually.")
                st.session_state.manual_scope_selection = True
    
    # Display scope data if available
    if st.session_state.scope_data:
        scope_data = st.session_state.scope_data
        
        st.subheader("Extracted Scope")
        st.write(f"Found on pages: {', '.join(map(str, scope_data.get('source_pages', [])))}")
        
        scope_text = scope_data.get("scope_text", "")
        if scope_text:
            st.text_area("Scope Text", value=scope_text, height=300, disabled=True)
            
            if not st.session_state.scope_confirmed:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Confirm Scope"):
                        result = api_client.confirm_document_scope(filename, scope_data.get('source_pages', []))
                        if "scope" in result:
                            st.session_state.scope_confirmed = True
                            st.success("Scope confirmed!")
                            return result["scope"]
                
                with col2:
                    if st.button("Reject and Select Pages Manually"):
                        st.session_state.scope_data = None
                        st.session_state.manual_scope_selection = True
                        st.session_state.scope_confirmed = False
            else:
                st.success("✓ Scope has been confirmed")
                return scope_data
        else:
            st.warning("No scope text was extracted.")
            st.session_state.manual_scope_selection = True
    
    # Manual scope selection
    if st.session_state.get("manual_scope_selection", False):
        st.subheader("Manual Scope Selection")
        st.write("Select the pages that contain the scope information:")
        
        # Create checkboxes for all pages
        total_pages = document_info.get("pages", 0)
        selected_pages = []
        
        # Group pages into rows to save space
        cols_per_row = 5
        for i in range(0, total_pages, cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                page_num = i + j + 1
                if page_num <= total_pages:
                    if cols[j].checkbox(f"Page {page_num}", key=f"page_{page_num}"):
                        selected_pages.append(page_num)
        
        # Show page content for selected pages
        if selected_pages:
            st.write(f"Selected pages: {', '.join(map(str, selected_pages))}")
            
            # Preview one page at a time
            preview_page = st.selectbox("Preview page:", selected_pages)
            
            if preview_page:
                with st.spinner(f"Loading page {preview_page}..."):
                    page_result = api_client.extract_page_text(filename, f"{preview_page}-{preview_page}")
                    if "text" in page_result:
                        st.text_area(f"Page {preview_page} Content", value=page_result["text"], height=300, disabled=True)
        
            # Confirm manual selection
            if st.button("Confirm Selected Pages"):
                if not selected_pages:
                    st.error("Please select at least one page")
                else:
                    with st.spinner("Processing selected pages..."):
                        result = api_client.confirm_document_scope(filename, selected_pages)
                        
                        if "scope" in result:
                            st.session_state.scope_data = result["scope"]
                            st.session_state.manual_scope_selection = False
                            st.session_state.scope_confirmed = True
                            st.success("Scope confirmed!")
                            return result["scope"]
                        else:
                            st.error(f"Error confirming scope: {result.get('message', 'Unknown error')}")
    
    return st.session_state.scope_data if st.session_state.scope_confirmed else None