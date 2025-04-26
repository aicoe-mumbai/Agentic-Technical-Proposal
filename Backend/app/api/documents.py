from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import os
import shutil
from typing import List, Dict, Any, Optional
import subprocess

from Backend.app.models.models import (
    DocumentUploadResponse, ScopeExtractionResponse, 
    ScopeConfirmationRequest, QueryRequest, RangeQueryRequest
)
from Backend.app.utils.pdf_utils import extract_text_from_pdf, extract_scope_from_document
from Backend.app.utils.vector_utils import initialize_vector_db, process_query
from Backend.app.core.config import UPLOADS_DIR

router = APIRouter(prefix="/documents", tags=["documents"])

# Dict to store active document session data
active_documents = {}

def check_tesseract_installed():
    """Check if tesseract is installed and accessible"""
    try:
        subprocess.run(['tesseract', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a new SOTR document (PDF)"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check if tesseract is installed
    if not check_tesseract_installed():
        raise HTTPException(
            status_code=500, 
            detail="Tesseract OCR is not installed. Please install tesseract-ocr package first."
        )
    
    # Save the file
    file_path = os.path.join(UPLOADS_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Add the document to active_documents before starting background task
    doc_id = os.path.basename(file_path)
    active_documents[doc_id] = {"status": "uploading", "message": "Document uploaded, processing will begin soon"}
    
    # Extract text and initialize vector DB in background
    background_tasks.add_task(process_document, file_path)
    
    return {
        "filename": file.filename,
        "file_path": file_path,
        "success": True,
        "message": "Document uploaded and queued for processing"
    }

@router.get("/{filename}/status")
async def document_status(filename: str):
    """Check document processing status"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    doc_id = os.path.basename(file_path)
    if doc_id not in active_documents:
        return {"status": "not_processed", "message": "Document exists but has not been processed"}
        
    return {
        "status": active_documents[doc_id]["status"],
        "message": active_documents[doc_id]["message"],
        "pages": active_documents[doc_id].get("total_pages", 0)
    }

@router.get("/{filename}/scope", response_model=ScopeExtractionResponse)
async def extract_document_scope(filename: str):
    """Extract the scope from the document"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    doc_id = os.path.basename(file_path)
    if doc_id not in active_documents or active_documents[doc_id]["status"] != "processed":
        raise HTTPException(status_code=400, detail="Document processing not complete")
    
    # Extract scope using the document's pages
    documents = extract_text_from_pdf(file_path, None)
    scope_data = extract_scope_from_document(documents)
    
    # Update the active document with scope data
    active_documents[doc_id]["scope"] = scope_data
    
    return scope_data

@router.post("/{filename}/confirm-scope")
async def confirm_document_scope(filename: str, request: ScopeConfirmationRequest):
    """Confirm or update the pages to use for scope extraction"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    doc_id = os.path.basename(file_path)
    if doc_id not in active_documents:
        raise HTTPException(status_code=400, detail="Document has not been processed")
    
    # Extract text from user-specified pages
    documents = extract_text_from_pdf(file_path, None)
    
    # Filter documents by user-selected pages
    selected_documents = [doc for doc in documents if doc.metadata.get("page") in request.page_numbers]
    
    if not selected_documents:
        raise HTTPException(status_code=400, detail="No valid pages selected")
    
    # Re-extract scope with user-confirmed pages
    scope_data = extract_scope_from_document(selected_documents)
    active_documents[doc_id]["scope"] = scope_data
    active_documents[doc_id]["scope_confirmed"] = True
    
    return {
        "message": "Scope confirmation successful",
        "scope": scope_data
    }

@router.post("/{filename}/query")
async def query_document(filename: str, request: QueryRequest):
    """Query the document for information"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    doc_id = os.path.basename(file_path)
    if doc_id not in active_documents or active_documents[doc_id]["status"] != "processed":
        raise HTTPException(status_code=400, detail="Document processing not complete")
    
    # Process query using vector search
    result = process_query(request.query)
    
    return {
        "query": request.query,
        "result": result
    }

@router.post("/{filename}/range-query")
async def range_query_document(filename: str, request: RangeQueryRequest):
    """Query the document with custom result range"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    doc_id = os.path.basename(file_path)
    if doc_id not in active_documents or active_documents[doc_id]["status"] != "processed":
        raise HTTPException(status_code=400, detail="Document processing not complete")
    
    # Process query using vector search with range
    result = process_query(request.query, result_range=(request.start_idx, request.end_idx))
    
    return {
        "query": request.query,
        "start_idx": request.start_idx,
        "end_idx": request.end_idx,
        "result": result
    }

@router.get("/{filename}/page/{page_range}")
async def extract_page_text(filename: str, page_range: str):
    """Extract text from specific pages"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    # Extract text from specific pages
    result = extract_text_from_pdf(file_path, page_range)
    
    if isinstance(result, str) and result.startswith("You are asking for too big"):
        raise HTTPException(status_code=400, detail=result)
    
    if isinstance(result, str) and result.startswith("The page range provided"):
        raise HTTPException(status_code=400, detail=result)
        
    return {
        "page_range": page_range,
        "text": result
    }

# Background task for document processing
def process_document(file_path: str):
    """Process the document in the background - extract text and initialize vector DB"""
    doc_id = os.path.basename(file_path)
    active_documents[doc_id] = {"status": "processing", "message": "Extracting text from document"}
    
    try:
        # Extract text from document
        documents = extract_text_from_pdf(file_path, None)
        
        if not isinstance(documents, list):
            active_documents[doc_id] = {
                "status": "error", 
                "message": "Error extracting text from document"
            }
            return
            
        active_documents[doc_id]["total_pages"] = len(documents)
        active_documents[doc_id]["message"] = "Initializing vector database"
        
        # Initialize vector DB
        success = initialize_vector_db(documents)
        
        if success:
            active_documents[doc_id] = {
                "status": "processed",
                "message": "Document processed successfully",
                "total_pages": len(documents)
            }
        else:
            active_documents[doc_id] = {
                "status": "error",
                "message": "Error initializing vector database"
            }
    
    except Exception as e:
        active_documents[doc_id] = {
            "status": "error",
            "message": f"Error processing document: {str(e)}"
        }