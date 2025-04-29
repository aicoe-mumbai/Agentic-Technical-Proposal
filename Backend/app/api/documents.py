from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import os
import shutil
from typing import List, Dict, Any, Optional
import subprocess

from Backend.app.models.models import (
    DocumentUploadResponse, ScopeExtractionResponse, 
    ScopeConfirmationRequest, QueryRequest, RangeQueryRequest,
    TopicListRequest
)
from Backend.app.utils.pdf_utils import extract_text_from_pdf
from Backend.app.utils.vector_utils import initialize_vector_db, process_query
from Backend.app.utils.rag_agent import RAGAgent
from Backend.app.core.config import UPLOADS_DIR
from Backend.app.core.state import active_documents
from Backend.app.db.database import (
    save_document, get_document, update_document_status,
    save_document_scope, get_document_scope,
    save_document_topics, get_document_topics
)

router = APIRouter(prefix="/documents", tags=["documents"])

def check_tesseract_installed():
    """Check if tesseract is installed and accessible"""
    try:
        subprocess.run(["tesseract", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
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
        
    # Initialize document in database
    doc_id = os.path.basename(file_path)
    save_document(
        doc_id=doc_id,
        filename=file.filename,
        file_path=file_path,
        status="uploading",
        message="Document uploaded, processing will begin soon"
    )
    
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
    doc_info = get_document(doc_id)
    
    if not doc_info:
        return {"status": "not_processed", "message": "Document exists but has not been processed"}
    
    # Get progress information from active_documents if available
    progress = 0
    if doc_id in active_documents:
        progress = active_documents[doc_id].get("progress", 0)
        
    return {
        "status": doc_info["status"],
        "message": doc_info["message"],
        "pages": doc_info.get("total_pages", 0),
        "progress": progress
    }

@router.get("/{filename}/scope", response_model=ScopeExtractionResponse)
async def extract_document_scope(filename: str):
    """Extract the scope from the document"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    doc_id = os.path.basename(file_path)
    doc_info = get_document(doc_id)
    
    if not doc_info or doc_info["status"] != "processed":
        raise HTTPException(status_code=400, detail="Document processing not complete")
    
    # Check if scope already exists
    existing_scope = get_document_scope(doc_id)
    if existing_scope and existing_scope.get("is_confirmed", False):
        # Update active_documents with the existing scope
        if doc_id not in active_documents:
            active_documents[doc_id] = {
                "status": "processed",
                "scope": existing_scope
            }
        else:
            active_documents[doc_id]["scope"] = existing_scope
        
        # Ensure is_complete is in the response
        if "is_complete" not in existing_scope:
            existing_scope["is_complete"] = True
            
        return existing_scope
    
    # Initialize RAG agent for scope extraction
    agent = RAGAgent(file_path, {})
    scope_data = agent.extract_scope()
    
    # Ensure is_complete is in the response
    if "is_complete" not in scope_data:
        scope_data["is_complete"] = bool(scope_data.get("scope_text", "").strip())
    
    # Save scope data
    save_document_scope(
        doc_id=doc_id,
        scope_text=scope_data["scope_text"],
        source_pages=scope_data["source_pages"],
        is_confirmed=False
    )
    
    # Update active_documents with the new scope
    if doc_id not in active_documents:
        active_documents[doc_id] = {
            "status": "processed",
            "scope": scope_data
        }
    else:
        active_documents[doc_id]["scope"] = scope_data
    
    return scope_data

@router.post("/{filename}/confirm-scope")
async def confirm_document_scope(filename: str, request: ScopeConfirmationRequest):
    """Confirm or update the pages to use for scope extraction"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    doc_id = os.path.basename(file_path)
    doc_info = get_document(doc_id)
    
    if not doc_info:
        raise HTTPException(status_code=400, detail="Document has not been processed")
    
    existing_scope = get_document_scope(doc_id)
    if not request.page_numbers and not existing_scope:
        raise HTTPException(status_code=400, detail="No scope data available to confirm")
    
    if request.page_numbers:
        # Extract text from user-specified pages
        documents = extract_text_from_pdf(file_path, None)
        
        # Filter documents by user-selected pages
        selected_documents = [doc for doc in documents if doc.metadata.get("page") in request.page_numbers]
        
        if not selected_documents:
            raise HTTPException(status_code=400, detail="No valid pages selected")
        
        # Re-extract scope with user-confirmed pages
        agent = RAGAgent(file_path, {})
        scope_data = agent.extract_scope()
    else:
        # Use existing scope data if no pages specified (direct confirmation)
        scope_data = existing_scope
    
    # Ensure is_complete is in the response
    if "is_complete" not in scope_data:
        scope_data["is_complete"] = bool(scope_data.get("scope_text", "").strip())
    
    # Update scope as confirmed
    save_document_scope(
        doc_id=doc_id,
        scope_text=scope_data["scope_text"],
        source_pages=scope_data["source_pages"],
        is_confirmed=True
    )
    
    # Update active_documents with the confirmed scope
    if doc_id not in active_documents:
        active_documents[doc_id] = {
            "status": "processed",
            "scope": scope_data
        }
    else:
        active_documents[doc_id]["scope"] = scope_data
    
    return {
        "message": "Scope confirmation successful",
        "scope": scope_data
    }

def process_document(file_path: str):
    """Process the document in the background - extract text and initialize vector DB"""
    doc_id = os.path.basename(file_path)
    update_document_status(doc_id, "processing", "Extracting text from document")
    
    # Update active_documents to show processing status
    active_documents[doc_id] = {
        "status": "processing",
        "message": "Extracting text from document",
        "progress": 0  # Initialize progress at 0%
    }
    
    try:
        # Extract text from document
        documents = extract_text_from_pdf(file_path, None)
        
        if not isinstance(documents, list):
            update_document_status(doc_id, "error", "Error extracting text from document")
            active_documents[doc_id] = {
                "status": "error",
                "message": "Error extracting text from document",
                "progress": 0
            }
            return
        
        # Document extraction complete - now at 60% progress
        update_document_status(
            doc_id=doc_id,
            status="processing",
            message="Initializing vector database",
            total_pages=len(documents)
        )
        
        active_documents[doc_id] = {
            "status": "processing",
            "message": "Initializing vector database",
            "total_pages": len(documents),
            "progress": 60  # Set progress to 60% after text extraction
        }
        
        # Initialize vector DB
        success = initialize_vector_db(documents)
        
        if success:
            update_document_status(
                doc_id=doc_id,
                status="processed",
                message="Document processed successfully",
                total_pages=len(documents)
            )
            
            active_documents[doc_id] = {
                "status": "processed",
                "message": "Document processed successfully",
                "total_pages": len(documents),
                "progress": 100  # Set progress to 100% when complete
            }
        else:
            update_document_status(
                doc_id=doc_id,
                status="error",
                message="Error initializing vector database"
            )
            
            active_documents[doc_id] = {
                "status": "error",
                "message": "Error initializing vector database",
                "progress": 0
            }
    
    except Exception as e:
        update_document_status(
            doc_id=doc_id,
            status="error",
            message=f"Error processing document: {str(e)}"
        )
        
        active_documents[doc_id] = {
            "status": "error",
            "message": f"Error processing document: {str(e)}",
            "progress": 0
        }

@router.post("/{filename}/topics/{template_name}")
async def save_document_topics_endpoint(filename: str, template_name: str, request: TopicListRequest):
    """Save topics for a document and template"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    doc_id = os.path.basename(file_path)
    
    # Save topics to database
    save_document_topics(doc_id, template_name, request.topics)
    
    return {"success": True, "message": "Topics saved successfully"}

@router.get("/{filename}/topics/{template_name}")
async def get_document_topics_endpoint(filename: str, template_name: str):
    """Get topics for a document and template"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    doc_id = os.path.basename(file_path)
    
    # Fetch topics from database
    topics = get_document_topics(doc_id, template_name)
    
    if not topics:
        return {"topics": []}
    
    return {"topics": topics}

@router.get("/{filename}/page/{page_range}")
async def extract_page_text_endpoint(filename: str, page_range: str):
    """Extract text from specific pages"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    try:
        text = extract_text_from_pdf(file_path, page_range)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")

@router.post("/{filename}/query")
async def query_document_endpoint(filename: str, request: QueryRequest):
    """Query the document"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    query = request.query
    result = process_query(query)
    
    return {"result": result}

@router.post("/{filename}/range-query")
async def range_query_document_endpoint(filename: str, request: RangeQueryRequest):
    """Query the document with custom result range"""
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    
    result = process_query(
        request.query,
        result_range=(request.start_idx, request.end_idx)
    )
    
    return {"result": result}