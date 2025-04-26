import streamlit as st
from typing import Dict, Any, List, Optional
import json

from Frontend.app.utils.api import api_client

def render_content_editor(document_info: Dict[str, Any], template_name: str, topics: List[Dict[str, Any]]):
    """
    Render the content editor for generating and editing proposal content
    
    Args:
        document_info: Dictionary with document information
        template_name: Name of the selected template
        topics: List of topic dictionaries
    """
    st.header("Content Editor")
    
    filename = document_info.get("filename")
    
    if not filename:
        st.error("No document selected")
        return
    
    if not template_name:
        st.error("No template selected")
        return
    
    if not topics:
        st.error("No topics available. Please generate topics first.")
        return
    
    # Initialize session state for content data
    if "content_data" not in st.session_state:
        st.session_state.content_data = {}
    
    # Get topics that aren't marked for removal
    valid_topics = [topic for topic in topics if topic.get("status") != "remove"]
    
    # Extract topic text and create a mapping to full topic data
    topic_texts = [f"{topic.get('number', '')} {topic.get('text', '')}" for topic in valid_topics]
    topic_map = {f"{topic.get('number', '')} {topic.get('text', '')}": topic for topic in valid_topics}
    
    # Topic selection
    selected_topic_text = st.selectbox("Select Topic to Generate", options=topic_texts)
    
    if selected_topic_text:
        selected_topic = topic_map[selected_topic_text]
        topic_key = json.dumps(selected_topic)
        
        # Generate content button
        if st.button("Generate Content") or (topic_key in st.session_state.content_data):
            # Show spinner only during initial generation
            if topic_key not in st.session_state.content_data:
                with st.spinner(f"Generating content for '{selected_topic_text}'..."):
                    result = api_client.generate_content(filename, template_name, selected_topic_text)
                    
                    if "content" in result:
                        st.session_state.content_data[topic_key] = result["content"]
                    else:
                        st.error("Failed to generate content.")
            
            # Display the content in the editor
            if topic_key in st.session_state.content_data:
                st.subheader("Content Editor")
                
                # Display the editor with existing content
                content = st.session_state.content_data[topic_key]
                edited_content = st.text_area("Edit Content", value=content, height=400)
                
                # Save edited content
                if edited_content != content:
                    st.session_state.content_data[topic_key] = edited_content
                
                # Buttons for content actions
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("Save"):
                        st.success("Content saved!")
                
                with col2:
                    if st.button("Copy to Clipboard"):
                        st.code(edited_content)
                        st.info("Use Ctrl+C to copy the content above")
                
                with col3:
                    if st.button("Download"):
                        topic_file_name = selected_topic_text.replace(' ', '_').replace('.', '_')
                        st.download_button(
                            label="Download Content", 
                            data=edited_content,
                            file_name=f"{topic_file_name}.txt", 
                            mime="text/plain"
                        )
    
    # Display the full document section
    if st.session_state.content_data:
        with st.expander("View Full Document", expanded=False):
            full_doc = ""
            
            # Create a hierarchy of topics and their content
            for topic_text in topic_texts:
                topic = topic_map[topic_text]
                topic_key = json.dumps(topic)
                
                if topic_key in st.session_state.content_data:
                    content = st.session_state.content_data[topic_key]
                    
                    # Add topic heading based on level
                    level = topic.get("level", 1)
                    heading = "#" * level
                    full_doc += f"{heading} {topic_text}\n\n{content}\n\n"
            
            # Display the full document
            st.markdown(full_doc)
            
            # Download full document button
            st.download_button(
                label="Download Full Document", 
                data=full_doc,
                file_name="full_proposal.md", 
                mime="text/markdown"
            ) 