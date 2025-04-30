import streamlit as st
import os
from typing import Dict, Any

# Import components
from Frontend.app.components.left_sidebar import render_left_sidebar
from Frontend.app.components.document_upload import render_document_upload
from Frontend.app.components.scope_extraction import render_scope_extraction
from Frontend.app.components.topics_display import render_topics_generation
from Frontend.app.components.content_editor import render_content_editor
from Frontend.app.components.chat_panel import render_chat_panel
from Frontend.app.components.document_writer import render_document_writer

# Import configuration
from Frontend.app.config import APP_TITLE, APP_DESCRIPTION, WIDE_MODE, ENABLE_THEME, CUSTOM_CSS
from Frontend.app.utils.api import api_client

def setup_page():
    """Set up the Streamlit page configuration"""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📝",
        layout="wide" if WIDE_MODE else "centered",
        initial_sidebar_state="expanded",
    )
    
    # Apply custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Page title
    st.title(APP_TITLE)
    st.markdown(f"<p>{APP_DESCRIPTION}</p>", unsafe_allow_html=True)
    
    # Apply the layout structure
    st.markdown('<div class="main-container">', unsafe_allow_html=True)

def initialize_app_state():
    """Initialize the application state"""
    # Initialize session state variables
    if "app_stage" not in st.session_state:
        st.session_state.app_stage = "upload"  # Stages: upload, scope, topics, content
    
    if "document_info" not in st.session_state:
        st.session_state.document_info = None
    
    if "scope_data" not in st.session_state:
        st.session_state.scope_data = None
    
    if "scope_confirmed" not in st.session_state:
        st.session_state.scope_confirmed = False
    
    if "topics_data" not in st.session_state:
        st.session_state.topics_data = None
    
    if "topics_finalized" not in st.session_state:
        st.session_state.topics_finalized = False
    
    if "finalized_topics" not in st.session_state:
        st.session_state.finalized_topics = None
    
    if "content_data" not in st.session_state:
        st.session_state.content_data = {}
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "skip_to_topics" not in st.session_state:
        st.session_state.skip_to_topics = False
    
    if "document_content" not in st.session_state:
        st.session_state.document_content = {}
    
    if "use_document_writer" not in st.session_state:
        st.session_state.use_document_writer = True

def main():
    """Main application entry point"""
    # Set up the page
    setup_page()
    
    # Initialize app state
    initialize_app_state()
    
    # Render left sidebar
    selected_project_name, project_data = render_left_sidebar()
    
    # Main content area
    main_column = st.container()
    
    with main_column:
        # Render document upload section
        document_info = render_document_upload()
        
        # Update session state document info
        if document_info:
            st.session_state.document_info = document_info
            
            # Set app stage to scope extraction if needed
            if document_info.get("status") == "processed" and st.session_state.app_stage == "upload":
                st.session_state.app_stage = "scope"
            
            # Check if we should skip directly to topics (when reuploading a previously processed document)
            if "previously_processed" in document_info and document_info["previously_processed"]:
                if st.session_state.scope_confirmed and selected_project_name:
                    # Try to load previously generated topics
                    try:
                        previous_topics = api_client.get_document_topics(document_info["filename"], selected_project_name)
                        if previous_topics and "topics" in previous_topics and previous_topics["topics"]:
                            st.session_state.topics_data = previous_topics
                            st.session_state.topics_finalized = True
                            st.session_state.app_stage = "topics"
                            st.session_state.skip_to_topics = True
                    except Exception as e:
                        # If there are no previous topics, continue with normal flow
                        pass
            
            # Render scope extraction if document is processed
            if document_info.get("status") == "processed":
                # Only show scope extraction if not skipping directly to topics
                if not st.session_state.skip_to_topics:
                    scope_data = render_scope_extraction(document_info)
                    
                    # Update scope data in session state
                    if scope_data:
                        st.session_state.scope_data = scope_data
                        st.session_state.scope_confirmed = True
                        
                        # Set app stage to topics generation if needed
                        if st.session_state.app_stage == "scope":
                            st.session_state.app_stage = "topics"
                
                # Only proceed if a project template is selected and scope is confirmed
                if selected_project_name and st.session_state.scope_confirmed and st.session_state.app_stage in ["topics", "content"]:
                    # Render topics generation
                    topics = render_topics_generation(document_info, selected_project_name)
                    
                    # If topics are finalized, update session state and proceed to content editor
                    if topics:
                        st.session_state.finalized_topics = topics
                        st.session_state.topics_finalized = True
                        
                        # Set app stage to content generation if needed
                        if st.session_state.app_stage == "topics":
                            st.session_state.app_stage = "content"
                        
                        # Render document writer or content editor based on preference
                        if st.session_state.app_stage == "content":
                            # Use document writer by default
                            render_document_writer(document_info, selected_project_name, topics)
    
    # Render chat panel in right sidebar
    # Use the right sidebar only if a document is loaded
    if st.session_state.document_info:
        render_chat_panel(st.session_state.document_info, selected_project_name)
    
    # Close the main container div
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main() 