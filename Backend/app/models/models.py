from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any

class ProjectTemplate(BaseModel):
    """Project template model"""
    project_name: str
    project_TOC: str
    file_path: str

class TemplateRequest(BaseModel):
    """Request model for creating a new template"""
    project_name: str
    project_TOC: str

class TemplateResponse(BaseModel):
    """Response model for template operations"""
    project_name: str
    project_TOC: str
    file_path: Optional[str] = None

class AllTemplatesResponse(BaseModel):
    """Response model for retrieving all templates"""
    templates: Dict[str, Dict[str, str]]

class TemplateUpdateRequest(BaseModel):
    """Request model for updating an existing template"""
    project_TOC: str
    # We can add excel_file: Optional[UploadFile] = File(None) later if needed for file updates

class DocumentSummaryItem(BaseModel):
    doc_id: str # This is typically the filename
    filename: str # Original filename, could be same as doc_id
    status: str
    created_at: Optional[str] = None # Or datetime
    total_pages: Optional[int] = None

class AllDocumentsResponse(BaseModel):
    documents: List[DocumentSummaryItem]

class DocumentUploadResponse(BaseModel):
    """Response model for document upload"""
    filename: str
    file_path: str
    success: bool
    message: str

class QueryRequest(BaseModel):
    """Request model for RAG queries"""
    query: str

class RangeQueryRequest(BaseModel):
    """Request model for range-based RAG queries"""
    query: str
    start_idx: int = 0
    end_idx: int = 3

class ScopeExtractionResponse(BaseModel):
    """Response model for scope extraction"""
    scope_text: str
    source_pages: List[Union[int, str]]
    is_complete: bool

class ScopeConfirmationRequest(BaseModel):
    """Request model for scope confirmation"""
    page_numbers: List[int]

class Topic(BaseModel):
    """Model for a single topic"""
    number: Optional[str] = None
    text: str
    level: int = 0
    status: str = "keep"
    page: Optional[int] = None
    id: Optional[int] = None
    is_confirmed: bool = False

class TopicListRequest(BaseModel):
    """Request model for saving topics"""
    topics: List[Dict[str, Any]]

class TopicGenerationResponse(BaseModel):
    """Response model for topic generation"""
    topics: List[Dict[str, Any]]
    raw_response: str

class ContentGenerationRequest(BaseModel):
    """Request model for content generation"""
    topic: str
    
class ContentGenerationResponse(BaseModel):
    """Response model for content generation"""
    content: str
    topic: str

class ChatRequest(BaseModel):
    """Request model for chat queries"""
    message: str
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list)

class ChatResponse(BaseModel):
    """Response model for chat interaction"""
    response: str
    status: str = "success" 