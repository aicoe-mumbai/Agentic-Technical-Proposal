import streamlit as st
from typing import Dict, Any, List, Optional
import re

from Frontend.app.utils.api import api_client

def render_topics_generation(document_info: Dict[str, Any], template_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Render the topics generation section
    
    Args:
        document_info: Dictionary with document information
        template_name: Name of the selected template
        
    Returns:
        List of topic dictionaries if generated successfully, None otherwise
    """
    st.header("Generate Topics")
    
    filename = document_info.get("filename")
    
    if not filename:
        st.error("No document selected")
        return None
    
    if not template_name:
        st.error("No template selected")
        return None
    
    if "topics_data" not in st.session_state:
        st.session_state.topics_data = None
    
    if st.button("Generate Topics"):
        with st.spinner("Generating topics based on document scope and template..."):
            result = api_client.generate_topics(filename, template_name)
            
            if "topics" in result and result["topics"]:
                st.session_state.topics_data = result
                st.success("Topics generated successfully!")
            else:
                st.error("Failed to generate topics. Please check if the document scope and template are valid.")
    
    # Display topics if available
    if st.session_state.topics_data:
        topics_data = st.session_state.topics_data
        topics = topics_data.get("topics", [])
        
        if not topics:
            st.warning("No topics generated")
            return None
        
        st.subheader("Generated Topics")
        
        # Container for topics
        st.markdown('<div class="topics-container">', unsafe_allow_html=True)
        
        for i, topic in enumerate(topics):
            # Process topic data
            topic_text = topic.get("text", "")
            topic_number = topic.get("number", "")
            topic_level = topic.get("level", 0)
            topic_status = topic.get("status", "keep")
            topic_page = topic.get("page", None)
            
            # Create a unique key for the topic
            topic_key = f"topic_{i}"
            
            # Determine the indentation based on level
            indent = "&nbsp;" * (4 * (topic_level - 1)) if topic_level > 0 else ""
            
            # Add number if available
            topic_display = f"{topic_number} {topic_text}" if topic_number else topic_text
            
            # Add page reference if available
            page_ref = f" (page {topic_page})" if topic_page else ""
            
            # Determine CSS class based on status
            css_class = f"topic-item {topic_status}"
            
            # Create edit icon
            edit_icon = "✏️"
            
            # Create the topic item with edit icon
            st.markdown(
                f'<div class="{css_class}" id="{topic_key}">{indent}{topic_display}{page_ref}'
                f'<span style="float:right">{edit_icon}</span></div>',
                unsafe_allow_html=True
            )
            
            # Allow editing if user clicks icon (not fully functional in Streamlit)
            # In a real application, add JavaScript for click handling
            if st.checkbox(f"Edit {topic_text}", key=f"edit_{topic_key}", label_visibility="collapsed"):
                edited_topic = st.text_input(f"Edit Topic", value=topic_text, key=f"edit_input_{topic_key}")
                if st.button(f"Save", key=f"save_{topic_key}"):
                    topic["text"] = edited_topic
                    st.experimental_rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # If topics need review, give option to view raw response
        if any(topic.get("status") == "remove" for topic in topics):
            st.warning("Some topics were marked for removal based on the document content.")
            
            # Show explanation if available
            if "raw_response" in topics_data:
                with st.expander("View Detailed Analysis"):
                    # Extract the "Additional Considerations" section if available
                    raw_response = topics_data["raw_response"]
                    considerations_match = re.search(r'\*\*Additional Considerations\*\*(.*?)$', raw_response, re.DOTALL)
                    
                    if considerations_match:
                        considerations = considerations_match.group(1).strip()
                        st.write(considerations)
                    else:
                        st.write(raw_response)
        
        # Allow the user to finalize the topics
        if st.button("Finalize Topics"):
            # Store the finalized topics in session state
            st.session_state.finalized_topics = topics
            st.success("Topics finalized! You can now proceed to content generation.")
            return topics
    
    return st.session_state.get("finalized_topics") 