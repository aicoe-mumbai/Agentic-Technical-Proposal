import re
import pytesseract
from pdf2image import convert_from_path
from langchain_core.documents import Document
from tqdm import tqdm
from typing import List, Optional, Union, Dict, Any
import os
from Backend.app.core.state import active_documents

def clean_string(input_string: str) -> str:
    """Clean and normalize a string by removing extra whitespace"""
    cleaned_string = re.sub(r'\s+', ' ', input_string)
    cleaned_string = cleaned_string.strip()
    return cleaned_string

def extract_text_from_pdf(pdf_path: str, pages_to_scrap: Optional[str] = None) -> Union[List[Document], str]:
    """Extract text from a PDF file with progress tracking"""
    pages = convert_from_path(pdf_path)
    max_pages = len(pages)
    doc_id = os.path.basename(pdf_path)

    if pages_to_scrap is None:
        # Scrap all pages and return as Document objects
        documents = []
        for i, page_image in enumerate(pages):
            # Update progress in active_documents
            progress = ((i + 1) / max_pages) * 100
            active_documents[doc_id].update({
                "status": "processing",
                "message": f"Extracting text from document ({progress:.1f}%)",
                "progress": progress
            })
            
            page_text = pytesseract.image_to_string(page_image).replace('Larsen & Toubro Design Competency Center ', '')
            doc = Document(page_content=clean_string(page_text), metadata={"page": i+1, "source": pdf_path})
            documents.append(doc)
        return documents

    else:
        # Scrap only the specified page range
        start, end = map(int, pages_to_scrap.split('-'))
        if (end - start + 1) > 3:
            return "You are asking for too big a page range. Set to a maximum of 3 pages."
            
        num_list = list(range(start - 1, end))
        num_list = [page for page in num_list if 0 <= page < max_pages]
        
        if not num_list:
            return "The page range provided is out of bounds."

        plain_text = ""
        for i, page_number in enumerate(num_list):
            progress = ((i + 1) / len(num_list)) * 100
            if doc_id in active_documents:
                active_documents[doc_id].update({
                    "status": "processing",
                    "message": f"Extracting text from selected pages ({progress:.1f}%)",
                    "progress": progress
                })
            
            page_image = pages[page_number]
            page_text = pytesseract.image_to_string(page_image).replace('Larsen & Toubro Design Competency Center ', '')
            plain_text += f"\n--- Page {page_number + 1} ---\n{page_text}"
        
        return clean_string(plain_text)

    """
    Extract the scope section from document list
    
    Args:
        documents: List of Document objects representing PDF pages
        
    Returns:
        Dictionary containing the extracted scope and source page references
    """
    scope_text = ""
    source_pages = []
    
    # Search for scope section across all documents
    for doc in documents:
        content = doc.page_content.lower()
        page_num = doc.metadata.get("page", "Unknown")
        
        # Look for scope keywords
        if "scope" in content and any(term in content for term in ["project scope", "scope of work", "scope of the project"]):
            # Extract paragraphs that seem to be part of the scope
            paragraphs = [p for p in content.split('\n\n') if p.strip() and any(scope_term in p.lower() 
                         for scope_term in ["scope", "include", "exclude", "deliver", "requirement"])]
            
            if paragraphs:
                scope_text += "\n".join(paragraphs) + "\n\n"
                source_pages.append(page_num)
    
    return {
        "scope_text": clean_string(scope_text),
        "source_pages": source_pages,
        "is_complete": bool(scope_text.strip())  # Indication if we found scope text
    }