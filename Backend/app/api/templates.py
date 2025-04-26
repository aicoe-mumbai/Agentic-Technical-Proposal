from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Dict, List, Optional
import os
import openpyxl

from Backend.app.models.models import (
    ProjectTemplate, TemplateRequest, TemplateResponse, AllTemplatesResponse
)
from Backend.app.db.database import save_template, get_all_templates, get_template_by_name, delete_template
from Backend.app.core.config import PROJECTS_DIR

router = APIRouter(prefix="/templates", tags=["templates"])

@router.get("/", response_model=AllTemplatesResponse)
async def list_templates():
    """List all available project templates"""
    templates = get_all_templates()
    return {"templates": templates}

@router.get("/{project_name}", response_model=TemplateResponse)
async def get_template(project_name: str):
    """Get a specific project template by name"""
    template = get_template_by_name(project_name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{project_name}' not found")
    return template

@router.post("/", response_model=TemplateResponse)
async def create_template(
    project_name: str = Form(...),
    project_TOC: str = Form(...),
    excel_file: Optional[UploadFile] = File(None)
):
    """Create a new project template with optional Excel file"""
    # Create project directory if it doesn't exist
    project_folder = os.path.join(PROJECTS_DIR, project_name)
    file_path = None
    
    if not os.path.exists(project_folder):
        os.makedirs(project_folder)
    
    # Save Excel file if provided
    if excel_file:
        file_path = os.path.join(project_folder, "template.xlsx")
        with open(file_path, "wb") as f:
            content = await excel_file.read()
            f.write(content)
    
    # Save template to database
    save_template(project_name, project_TOC, file_path or "")
    
    return {
        "project_name": project_name,
        "project_TOC": project_TOC,
        "file_path": file_path
    }

@router.delete("/{project_name}")
async def remove_template(project_name: str):
    """Delete a project template"""
    success = delete_template(project_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Template '{project_name}' not found")
    return {"message": f"Template '{project_name}' deleted successfully"}

@router.get("/{project_name}/data")
async def get_template_data(project_name: str):
    """Get Excel data from a template as key-value pairs"""
    template = get_template_by_name(project_name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{project_name}' not found")
    
    file_path = template.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Excel file for template '{project_name}' not found")
    
    try:
        wb = openpyxl.load_workbook(file_path)
        ws = wb['Sheet1']
        data_dict = {}
        for i in range(2, ws.max_row + 1):
            key = ws.cell(i, 1).value
            value = ws.cell(i, 2).value
            if key is not None and value is not None:
                data_dict[key] = value
        return data_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading Excel file: {str(e)}") 