import streamlit as st
from typing import Dict, Any, List, Optional

from Frontend.app.utils.api import api_client

def render_chat_panel(document_info: Dict[str, Any], template_name: str):
    """
    Render the chat panel for interacting with the document
    
    Args:
        document_info: Dictionary with document information
        template_name: Name of the selected template
    """
    st.sidebar.header("Chat with Document")
    
    filename = document_info.get("filename") if document_info else None
    
    if not filename:
        st.sidebar.warning("Please upload a document first")
        return
    
    if not template_name:
        st.sidebar.warning("Please select a template first")
        return
    
    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display the chat history
    for message in st.session_state.chat_history[-5:]:  # Show last 5 messages
        if "user" in message:
            st.sidebar.markdown(
                f'<div class="chat-message user-message">'
                f'<strong>User:</strong> {message["user"]}'
                f'</div>', 
                unsafe_allow_html=True
            )
        if "agent" in message:
            st.sidebar.markdown(
                f'<div class="chat-message agent-message">'
                f'<strong>Agent:</strong> {message["agent"]}'
                f'</div>', 
                unsafe_allow_html=True
            )
    
    # Chat input
    user_input = st.sidebar.text_input("Enter your message", key="user_message")
    
    if st.sidebar.button("Send") and user_input:
        # Add user message to history
        st.session_state.chat_history.append({"user": user_input})
        
        # Get response from API
        with st.spinner("Thinking..."):
            response = api_client.chat_with_document(
                filename, 
                template_name, 
                user_input, 
                st.session_state.chat_history
            )
            
            if "response" in response:
                # Add agent response to history
                st.session_state.chat_history.append({"agent": response["response"]})
                
                # Force a rerun to update the display
                st.experimental_rerun()
    
    # Add a clear button for chat history
    if st.session_state.chat_history and st.sidebar.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.experimental_rerun() 