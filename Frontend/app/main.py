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

# Import configuration
from Frontend.app.config import APP_TITLE, APP_DESCRIPTION, WIDE_MODE, ENABLE_THEME, CUSTOM_CSS

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
    
    if "topics_data" not in st.session_state:
        st.session_state.topics_data = None
    
    if "finalized_topics" not in st.session_state:
        st.session_state.finalized_topics = None
    
    if "content_data" not in st.session_state:
        st.session_state.content_data = {}
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

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
            
            # Render scope extraction if document is processed
            if document_info.get("status") == "processed":
                scope_data = render_scope_extraction(document_info)
                
                # If scope is extracted, proceed to topics generation
                if scope_data:
                    st.session_state.scope_data = scope_data
                    
                    # Only proceed if a project template is selected
                    if selected_project_name:
                        # Render topics generation
                        topics = render_topics_generation(document_info, selected_project_name)
                        
                        # If topics are finalized, proceed to content editor
                        if topics:
                            st.session_state.finalized_topics = topics
                            
                            # Render content editor
                            render_content_editor(document_info, selected_project_name, topics)
    
    # Render chat panel in right sidebar
    # Use the right sidebar only if a document is loaded
    if st.session_state.document_info:
        render_chat_panel(st.session_state.document_info, selected_project_name)
    
    # Close the main container div
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main() 