import streamlit as st
import json
import time
from typing import Dict, Any, List, Optional

from Frontend.app.utils.api import api_client

def render_document_writer(document_info: Dict[str, Any], template_name: str, topics: List[Dict[str, Any]]):
    """
    Render the document writer with auto-generation of all topics and proper formatting
    
    Args:
        document_info: Dictionary with document information
        template_name: Name of the selected template
        topics: List of topic dictionaries
    """
    st.header("Document Writer")
    
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
    
    # Initialize session state for document writer
    if "document_content" not in st.session_state:
        st.session_state.document_content = {}
    
    if "current_topic_index" not in st.session_state:
        st.session_state.current_topic_index = 0
    
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False
    
    if "document_saved" not in st.session_state:
        st.session_state.document_saved = False
    
    if "content_loaded" not in st.session_state:
        st.session_state.content_loaded = False
    
    # Get topics that aren't marked for removal
    valid_topics = [topic for topic in topics if topic.get("status") != "remove"]
    
    # Load previously saved content if not already loaded
    if not st.session_state.content_loaded:
        try:
            # Try to load content for each topic
            content_loaded = False
            for topic in valid_topics:
                topic_id = topic.get("id", 0)
                if topic_id == 0:
                    topic_id = valid_topics.index(topic) + 1
                
                # Get content from API
                result = api_client.get_document_content(filename, topic_id)
                if result.get("exists", False) and result.get("content"):
                    topic_key = json.dumps(topic)
                    st.session_state.document_content[topic_key] = result["content"]
                    content_loaded = True
            
            # Mark as loaded regardless of result to avoid repeated API calls
            st.session_state.content_loaded = True
            
            if content_loaded:
                st.success("Previously saved content loaded successfully!")
        except Exception as e:
            st.error(f"Error loading document content: {str(e)}")
            # Mark as loaded to avoid repeated API calls even if it fails
            st.session_state.content_loaded = True
    
    # Show progress and controls in sidebar
    progress_col, controls_col = st.columns([3, 1])
    
    with progress_col:
        progress_percentage = 0
        if valid_topics:
            progress_percentage = min(100, int((len(st.session_state.document_content) / len(valid_topics)) * 100))
        
        progress_text = f"Progress: {len(st.session_state.document_content)}/{len(valid_topics)} topics"
        st.progress(progress_percentage / 100)
        st.write(progress_text)
    
    with controls_col:
        if not st.session_state.is_generating and progress_percentage < 100:
            if st.button("Generate All"):
                st.session_state.is_generating = True
                st.experimental_rerun()
    
    # Auto-generate content for all topics if requested
    if st.session_state.is_generating and progress_percentage < 100:
        with st.spinner(f"Generating document content ({progress_percentage}% complete)"):
            # Find the next topic without content
            for i, topic in enumerate(valid_topics):
                topic_key = json.dumps(topic)
                if topic_key not in st.session_state.document_content:
                    topic_text = f"{topic.get('number', '')} {topic.get('text', '')}".strip()
                    
                    # Generate content for this topic
                    try:
                        result = api_client.generate_content(filename, template_name, topic_text)
                        if "content" in result:
                            st.session_state.document_content[topic_key] = result["content"]
                            # Add a small delay to prevent overloading the API
                            time.sleep(0.5)
                    except Exception as e:
                        st.error(f"Error generating content for '{topic_text}': {str(e)}")
                    
                    break
            
            # Check if all topics have been generated
            if len(st.session_state.document_content) >= len(valid_topics):
                st.session_state.is_generating = False
            
            # Rerun to show progress and continue generation
            st.experimental_rerun()
    
    # Display the full document in a formatted canvas
    st.subheader("Document Preview")
    
    # Create styled container for document
    st.markdown('<div class="document-canvas">', unsafe_allow_html=True)
    
    # Use a container to style the document
    document_container = st.container()
    
    with document_container:
        # Create and display the full document with proper formatting
        full_document = ""
        
        # Add document title
        full_document += f"<h1 style='text-align:center;'>{template_name}</h1>\n\n"
        
        # Add each topic with its content
        for topic in valid_topics:
            topic_key = json.dumps(topic)
            topic_text = topic.get("text", "")
            topic_number = topic.get("number", "")
            topic_level = topic.get("level", 1)
            
            # Add formatted topic heading
            if topic_level == 1:
                heading_tag = f"<h2>{topic_number} {topic_text}</h2>"
            elif topic_level == 2:
                heading_tag = f"<h3>{topic_number} {topic_text}</h3>"
            else:
                heading_tag = f"<h4>{topic_number} {topic_text}</h4>"
            
            full_document += heading_tag + "\n\n"
            
            # Add formatted topic content if available
            if topic_key in st.session_state.document_content:
                content = st.session_state.document_content[topic_key]
                
                # Format content with proper styling
                formatted_content = format_content(content)
                full_document += formatted_content + "\n\n"
            else:
                # Placeholder for topics not yet generated
                full_document += "<p><em>Content will be generated for this section...</em></p>\n\n"
        
        # Display the formatted document
        st.markdown(full_document, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Document actions
    st.subheader("Document Actions")
    
    # Row of buttons for actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Save Document"):
            try:
                # Save each topic's content to the database
                content_items = []
                for topic in valid_topics:
                    topic_key = json.dumps(topic)
                    if topic_key in st.session_state.document_content:
                        content = st.session_state.document_content[topic_key]
                        topic_id = topic.get("id", 0)
                        # If we don't have a topic ID (which might happen), use the index
                        if topic_id == 0:
                            topic_id = valid_topics.index(topic) + 1
                        
                        # Add to content items for bulk save
                        content_items.append({
                            "topic_id": topic_id,
                            "content": content
                        })
                
                # Save all content items at once
                if content_items:
                    result = api_client.save_document_content_bulk(filename, content_items)
                    if result.get("success", False):
                        st.session_state.document_saved = True
                        st.success("Document saved successfully!")
                    else:
                        st.error(f"Error saving document: {result.get('message', 'Unknown error')}")
                else:
                    st.warning("No content to save")
            except Exception as e:
                st.error(f"Error saving document: {str(e)}")
    
    with col2:
        if st.button("Export as Word"):
            # Placeholder for Word export - could be implemented later
            st.info("Word export feature coming soon!")
    
    with col3:
        # Download as Markdown
        markdown_content = convert_to_markdown(valid_topics, st.session_state.document_content, template_name)
        st.download_button(
            label="Download as Markdown",
            data=markdown_content,
            file_name=f"{filename.replace('.pdf', '')}_proposal.md",
            mime="text/markdown"
        )
    
    # Individual topic editor
    if valid_topics:
        st.subheader("Edit Individual Sections")
        
        # Topic selection with numbers for better organization
        topic_options = []
        for i, topic in enumerate(valid_topics):
            topic_text = topic.get("text", "")
            topic_number = topic.get("number", "")
            display_text = f"{topic_number} {topic_text}" if topic_number else topic_text
            topic_options.append(f"{i+1}. {display_text}")
        
        selected_topic_index = st.selectbox("Select a section to edit:", 
                                           options=range(len(topic_options)), 
                                           format_func=lambda x: topic_options[x])
        
        if selected_topic_index is not None:
            topic = valid_topics[selected_topic_index]
            topic_key = json.dumps(topic)
            topic_text = f"{topic.get('number', '')} {topic.get('text', '')}".strip()
            
            # Generate button only if content doesn't exist
            if topic_key not in st.session_state.document_content:
                if st.button(f"Generate Content for '{topic_text}'"):
                    with st.spinner(f"Generating content for '{topic_text}'..."):
                        result = api_client.generate_content(filename, template_name, topic_text)
                        if "content" in result:
                            st.session_state.document_content[topic_key] = result["content"]
                            st.success("Content generated!")
                            st.experimental_rerun()
            
            # Editor for the topic content
            if topic_key in st.session_state.document_content:
                content = st.session_state.document_content[topic_key]
                
                edited_content = st.text_area(
                    f"Edit Content for '{topic_text}'",
                    value=content,
                    height=300
                )
                
                # Save topic edits
                if edited_content != content:
                    if st.button("Save Edits"):
                        st.session_state.document_content[topic_key] = edited_content
                        st.success("Edits saved!")
                        st.session_state.document_saved = False

def format_content(content: str) -> str:
    """
    Format content with proper HTML styling
    
    Args:
        content: Raw content text
        
    Returns:
        Formatted content with HTML styling
    """
    # Replace line breaks with paragraph tags
    paragraphs = content.split('\n\n')
    formatted_content = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # Check for lists
        if paragraph.startswith('* ') or paragraph.startswith('- '):
            lines = paragraph.split('\n')
            formatted_content += "<ul>\n"
            for line in lines:
                line = line.strip()
                if line.startswith('* ') or line.startswith('- '):
                    item = line[2:].strip()
                    formatted_content += f"<li>{item}</li>\n"
            formatted_content += "</ul>\n"
        
        # Check for numbered lists
        elif paragraph.strip().startswith('1. '):
            lines = paragraph.split('\n')
            formatted_content += "<ol>\n"
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and line[1:].startswith('. '):
                    item = line[line.find(' ')+1:].strip()
                    formatted_content += f"<li>{item}</li>\n"
            formatted_content += "</ol>\n"
        
        # Check for headings (assuming markdown-like syntax)
        elif paragraph.startswith('# '):
            heading = paragraph[2:].strip()
            formatted_content += f"<h2>{heading}</h2>\n"
        elif paragraph.startswith('## '):
            heading = paragraph[3:].strip()
            formatted_content += f"<h3>{heading}</h3>\n"
        elif paragraph.startswith('### '):
            heading = paragraph[4:].strip()
            formatted_content += f"<h4>{heading}</h4>\n"
        
        # Bold text (assuming markdown-like syntax)
        elif '**' in paragraph:
            # Process each line separately
            lines = paragraph.split('\n')
            for line in lines:
                # Replace bold syntax with HTML
                while '**' in line:
                    line = line.replace('**', '<strong>', 1)
                    if '**' in line:
                        line = line.replace('**', '</strong>', 1)
                formatted_content += f"<p>{line}</p>\n"
        
        # Regular paragraphs
        else:
            formatted_content += f"<p>{paragraph}</p>\n"
    
    return formatted_content

def convert_to_markdown(topics: List[Dict[str, Any]], content_map: Dict[str, str], title: str) -> str:
    """
    Convert document to Markdown format for export
    
    Args:
        topics: List of topic dictionaries
        content_map: Map of topic keys to content
        title: Document title
        
    Returns:
        Document as Markdown string
    """
    markdown = f"# {title}\n\n"
    
    for topic in topics:
        topic_key = json.dumps(topic)
        topic_text = topic.get("text", "")
        topic_number = topic.get("number", "")
        topic_level = topic.get("level", 1)
        
        # Add topic heading with appropriate level
        heading_prefix = "#" * (topic_level + 1)
        markdown += f"{heading_prefix} {topic_number} {topic_text}\n\n"
        
        # Add topic content
        if topic_key in content_map:
            markdown += f"{content_map[topic_key]}\n\n"
        else:
            markdown += "*Content not generated for this section.*\n\n"
    
    return markdown

# Add this to config.py for styling
DOCUMENT_WRITER_CSS = """
.document-canvas {
    border: 1px solid #ddd;
    padding: 2rem;
    margin: 1rem 0;
    border-radius: 5px;
    background-color: white;
    min-height: 800px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.document-canvas h1, .document-canvas h2, .document-canvas h3, .document-canvas h4 {
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    font-weight: bold;
}

.document-canvas h1 {
    font-size: 1.8rem;
    text-align: center;
    border-bottom: 1px solid #eee;
    padding-bottom: 1rem;
}

.document-canvas h2 {
    font-size: 1.5rem;
    border-bottom: 1px solid #f0f0f0;
    padding-bottom: 0.5rem;
}

.document-canvas h3 {
    font-size: 1.3rem;
}

.document-canvas h4 {
    font-size: 1.1rem;
}

.document-canvas p {
    margin-bottom: 1rem;
    line-height: 1.6;
    text-align: justify;
}

.document-canvas ul, .document-canvas ol {
    margin-bottom: 1rem;
    padding-left: 2rem;
}

.document-canvas li {
    margin-bottom: 0.5rem;
    line-height: 1.5;
}

.document-canvas strong {
    font-weight: bold;
}

.document-canvas em {
    font-style: italic;
}

@media print {
    .document-canvas {
        border: none;
        box-shadow: none;
        padding: 0;
    }
}
""" 