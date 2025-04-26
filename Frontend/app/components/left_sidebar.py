import streamlit as st
import os
from typing import Dict, Any, Tuple, Optional

from Frontend.app.utils.api import api_client

def render_left_sidebar() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Render the left sidebar with project configuration options
    
    Returns:
        Tuple containing (selected_project_name, project_data)
    """
    st.sidebar.title("Configuration")
    
    # Create New Project Section
    st.sidebar.subheader("Create New Project")
    
    new_project_name = st.sidebar.text_input("Enter new Project Name")
    toc_template = st.sidebar.text_area("Enter the possible Topics to cover with sections and subsections")
    
    # Initialize session state for replacement confirmation
    if 'show_replace_confirm' not in st.session_state:
        st.session_state.show_replace_confirm = False
    
    # Add save button before Excel upload
    if new_project_name and toc_template and st.sidebar.button("Save Project"):
        # Check if project already exists
        existing_projects = api_client.get_templates()
        if new_project_name in existing_projects:
            st.session_state.show_replace_confirm = True
        else:
            result = api_client.create_template(new_project_name, toc_template, None)
            if result:
                st.sidebar.success(f"Project '{new_project_name}' saved successfully!")
                st.experimental_rerun()

    # Show replacement confirmation if needed
    if st.session_state.show_replace_confirm:
        if st.sidebar.checkbox("Project already exists. Do you want to replace it?"):
            result = api_client.create_template(new_project_name, toc_template, None)
            if result:
                st.sidebar.success(f"Project '{new_project_name}' updated successfully!")
                st.session_state.show_replace_confirm = False
                st.experimental_rerun()
    
    uploaded_excel = st.sidebar.file_uploader("Upload Template Excel File for New Project", type=["xlsx"])
    
    # Initialize session state for Excel replacement confirmation
    if 'show_excel_replace_confirm' not in st.session_state:
        st.session_state.show_excel_replace_confirm = False
    
    if uploaded_excel and st.sidebar.button("Save Project with Excel"):
        # Check if project already exists
        existing_projects = api_client.get_templates()
        if new_project_name in existing_projects:
            st.session_state.show_excel_replace_confirm = True
        else:
            result = api_client.create_template(new_project_name, toc_template, uploaded_excel)
            if result:
                st.sidebar.success(f"Project '{new_project_name}' saved with Excel template successfully!")
                st.experimental_rerun()

    # Show Excel replacement confirmation if needed
    if st.session_state.show_excel_replace_confirm:
        if st.sidebar.checkbox("Project already exists. Do you want to replace it with Excel template?"):
            result = api_client.create_template(new_project_name, toc_template, uploaded_excel)
            if result:
                st.sidebar.success(f"Project '{new_project_name}' updated with Excel template successfully!")
                st.session_state.show_excel_replace_confirm = False
                st.experimental_rerun()
                
    # Select Existing Project Section
    st.sidebar.subheader("Select Project Name")
    
    # Fetch all templates
    project_data = api_client.get_templates()
    
    selected_project_name = st.sidebar.selectbox(
        "Select Project Template", 
        options=list(project_data.keys()),
        index=0 if project_data else None,
        key="project_selector"
    )
    
    if selected_project_name:
        selected_project = project_data[selected_project_name]
        given_toc = selected_project["project_TOC"]
        st.sidebar.text_area("Template Format", value=given_toc, height=200, disabled=True)
        
        # Initialize session state for delete confirmation
        if 'show_delete_confirm' not in st.session_state:
            st.session_state.show_delete_confirm = False
        
        if st.sidebar.button("Delete Project"):
            st.session_state.show_delete_confirm = True
        
        # Show delete confirmation if needed
        if st.session_state.show_delete_confirm:
            if st.sidebar.checkbox("Are you sure you want to delete this project?"):
                response = api_client.delete_template(selected_project_name)
                if response:
                    st.sidebar.success(f"Project '{selected_project_name}' deleted successfully!")
                    st.session_state.show_delete_confirm = False
                    st.experimental_rerun()
    
    return selected_project_name, project_data