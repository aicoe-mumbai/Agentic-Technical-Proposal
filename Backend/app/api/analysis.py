from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, List, Optional, Any
import os
import re
import logging
from Backend.app.models.models import (
    TopicGenerationResponse, ContentGenerationRequest, 
    ContentGenerationResponse, ChatRequest, ChatResponse
)
from Backend.app.utils.rag_agent import RAGAgent
from Backend.app.db.database import get_template_by_name, get_document, get_document_scope
from Backend.app.core.config import UPLOADS_DIR, PROJECTS_DIR, BASE_DIR as PROJECT_ROOT
from Backend.app.core.state import active_documents
import openpyxl

router = APIRouter(prefix="/analysis", tags=["analysis"])
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_template_data_dict(template_name: str) -> dict:
    """Load template file and return a key-value dictionary from its first two columns."""
    template = get_template_by_name(template_name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")

    relative_file_path = template.get("file_path")
    if not relative_file_path:
        raise HTTPException(status_code=404, detail=f"Template file path not defined for '{template_name}'")

    # Construct absolute path
    absolute_file_path = os.path.join(PROJECT_ROOT, relative_file_path)
    logger.info(f"Constructed absolute path for template '{template_name}': {absolute_file_path}")

    if not os.path.exists(absolute_file_path):
        logger.error(f"Template file not found at absolute path: {absolute_file_path}")
        raise HTTPException(status_code=404, detail=f"Template file for '{template_name}' not found at {absolute_file_path}")

    try:
        wb = openpyxl.load_workbook(absolute_file_path)
        ws = wb.active
        data_dict = {}
        for row in ws.iter_rows(min_row=2, max_col=2, values_only=True):
            key, value = row
            if key is not None and value is not None:
                data_dict[key] = value
        return data_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading template data: {e}")
    

@router.post("/generate-topics/{document_name:path}/{template_name}", response_model=TopicGenerationResponse)
async def generate_topics(document_name: str, template_name: str):
    """Ensure document processed, initialize agent, and generate topics based on scope and template."""
    # Validate document
    doc_path = os.path.join(UPLOADS_DIR, document_name)
    logger.info(f"Attempting to generate topics for document: {document_name} at path: {doc_path}")
    if not os.path.exists(doc_path):
        logger.error(f"Document not found at path: {doc_path}")
        raise HTTPException(status_code=404, detail=f"Document '{document_name}' not found")

    doc_id = os.path.basename(doc_path)
    doc_data_from_state = active_documents.get(doc_id) # Get from in-memory state first
    logger.info(f"Retrieved doc_data from active_documents for {doc_id}: {doc_data_from_state}")

    # Attempt to get document info from DB if not in active_documents or status incorrect
    db_doc_info = get_document(doc_id) # Fetch from DB
    if not db_doc_info or db_doc_info.get("status") != "processed":
        logger.error(f"Document {doc_id} not found in DB or not processed. DB status: {db_doc_info.get('status') if db_doc_info else 'Not in DB'}")
        raise HTTPException(status_code=400, detail=f"Document {doc_id} has not been processed or is not found in database.")

    # Validate and load template data
    data_dict = get_template_data_dict(template_name)
    agent = RAGAgent(doc_path, data_dict) # RAGAgent initialization needs doc_path

    # Try to get scope from active_documents first, then from DB
    scope_info = None
    if doc_data_from_state:
        scope_info = doc_data_from_state.get("scope")
        logger.info(f"Scope from active_documents for {doc_id}: {scope_info}")
    
    if not scope_info or not scope_info.get("is_confirmed"):
        logger.info(f"Scope not in active_documents or not confirmed, fetching from DB for {doc_id}")
        scope_info_from_db = get_document_scope(doc_id) # Fetch from DB
        if scope_info_from_db and scope_info_from_db.get("is_confirmed"):
            logger.info(f"Using scope from DB for {doc_id}: {scope_info_from_db}")
            scope_info = scope_info_from_db
        else:
            logger.warning(f"Scope for {doc_id} not found in DB or not confirmed. DB scope: {scope_info_from_db}")
            # Keep current scope_info (which might be None or unconfirmed from active_documents)
            # The check below will handle it

    logger.info(f"Final scope_info for {doc_id} before validation: {scope_info}")

    if not scope_info or not scope_info.get("scope_text") or not scope_info.get("is_confirmed"):
        error_detail = "Document scope missing, empty, or not confirmed. Please extract and confirm scope first."
        if scope_info and not scope_info.get("is_confirmed"):
            error_detail = "Document scope has been extracted but not confirmed. Please confirm scope first."
        elif not scope_info or not scope_info.get("scope_text"):
            error_detail = "Document scope has not been extracted or is empty. Please extract scope first."
        logger.error(f"Validation failed: {error_detail} for {doc_id}. Scope text present: {'scope_text' in scope_info if scope_info else False}, Confirmed: {scope_info.get('is_confirmed') if scope_info else False}")
        raise HTTPException(status_code=400, detail=error_detail)

    # Load template TOC
    template = get_template_by_name(template_name)
    toc = template.get("project_TOC") if template else None
    logger.info(f"Retrieved template '{template_name}' TOC: {'Present' if toc else 'Missing or Empty'}")

    if not toc:
        logger.error(f"Validation failed: Template '{template_name}' has no ToC defined.")
        raise HTTPException(status_code=400, detail=f"Template '{template_name}' has no ToC defined")
    # Build prompt
    prompt = f"""
        Develop a hierarchical Table of Contents (ToC) by validating the content of the uploaded Statement of Technical Requirements (SOTR) document against the provided Example ToC.

        Table of Contents (ToC):
        {toc}

        ### Scope Information:
        {scope_info['scope_text']}
        (Found on pages: {', '.join(map(str, scope_info.get('source_pages', [])))})

        ### Instructions:
        1. For each item in the ToC:
        - Search for the exact term, related technical terms, and component/subsystem terms using MilvusSimilaritySearchTool.
        - Document evidence found or indicate absence.
        - Never assume presence without tool verification.
        2. Decision Criteria:
        - Keep items with clear evidence.
        - Mark items for removal if evidence is missing.
        - Highlight new additions found in the SOTR.
        3. Required Output:
        Provide the updated ToC as plain text (preserving hierarchy) and annotate items needing removal with [REMOVE] and new additions with [ADD]. Include page numbers where evidence is found.
        4. Process:
        - Process every item.
        - Skip common sections (e.g., Preamble, Introduction, Scope, Delivery) without search.
        - Show search attempts for each item.

        Your output must strictly follow the format:
        **Updated TOC**
        1. Preamble
        2. Introduction
        3. IPMS (page 7)
        3.1 Propulsion system (page 8)
        3.2 Alarm system [REMOVE]
        ...
        **Additional Considerations**
        1) Evidences
        2) Why topics removed
        3) Annotations
        """
    # Generate topics
    try:
        raw_output = agent.request_invoker({"input": prompt})
        if not raw_output:
            raise ValueError("Empty response from agent")
        topics = parse_topics_from_response(raw_output)
        return {"topics": topics, "raw_response": raw_output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating topics: {e}")

@router.post("/generate-content/{document_name}/{template_name}", response_model=ContentGenerationResponse)
async def generate_content(
    document_name: str, 
    template_name: str, 
    request: ContentGenerationRequest
):
    """Generate content for a specific topic"""
    try:
        logger.info(f"Starting content generation for document: {document_name}, template: {template_name}, topic: {request.topic}")
        data_dict = get_template_data_dict(template_name)
        # Get or create agent with proper error handling
        try:
            agent = RAGAgent(document_name, data_dict)
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error initializing agent: {str(e)}")
        
        # Get scope data with validation
        doc_id = os.path.basename(os.path.join(UPLOADS_DIR, document_name))
        if doc_id not in active_documents:
            logger.error(f"Document {document_name} not found in active documents")
            raise HTTPException(
                status_code=400, 
                detail=f"Document {document_name} not found in active documents"
            )
            
        if "scope" not in active_documents[doc_id]:
            logger.error(f"No scope data found for document {document_name}")
            raise HTTPException(
                status_code=400, 
                detail="Document scope has not been extracted"
            )
        
        scope_data = active_documents[doc_id]["scope"]
        
        # Content generation prompt
        content_prompt = """
        You are an advanced AI assistant supporting a skilled engineering team in drafting high-level technical proposal content.
        Use the previously generated content from the ContentGenerationTemplateTool as a baseline.
        Your task is to update only the key parameters, data points, and specifications based on the current Statement of Technical Requirements (SOTR), while retaining the overall structure and flow.

        Workflow:
        1. Retrieve the existing content from ContentGenerationTemplateTool.
        2. Identify key parameters needing update (e.g., quantities, technical specifications, metrics).
        3. Extract updated details from the current SOTR using MilvusSimilaritySearchTool or PDFTextExtractorTool.
        4. Revise the content by incorporating the updates, ensuring consistency and clarity.

        Guidelines:
        - Retain the original content structure, modifying only necessary details.
        - For each update, provide a brief explanation.
        - Present the updated content as clean, plain text (no HTML styling).
        - Generate detailed content that accurately reflects the requirements in the SOTR.
        - Validate all extracted information with exact page references.
        - For any technical specifications, include units and tolerances if specified.
        """

        # User input for the agent
        user_input = f"""
        User Selected Topic: {request.topic}
        
        Scope Context:
        {scope_data.get('scope_text', 'No scope available')}
        (Found on pages: {', '.join(map(str, scope_data.get('source_pages', [])))})
        """
        
        # Create the combined prompt
        combined_prompt = f"{content_prompt}\n\n{user_input}"
        
        logger.info("Sending content prompt to agent")
        try:
            # Send to agent
            content = agent.request_invoker({"input": combined_prompt})
            
            if not content:
                raise ValueError("Empty response from agent")
                
            logger.info(f"Successfully generated content for topic: {request.topic}")
            return {
                "content": content,
                "topic": request.topic
            }
            
        except Exception as e:
            logger.error(f"Error in agent processing: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in content generation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/chat/{document_name}/{template_name}", response_model=ChatResponse)
async def chat_with_document(
    document_name: str, 
    template_name: str, 
    request: ChatRequest
):
    """Chat with the document using the RAG agent"""
    data_dict = get_template_data_dict(template_name)
    agent = RAGAgent(document_name, data_dict)
    
    # Prepare chat prompt
    chat_prompt = """
You are a **Technical Proposal Generation Agent** designed to create high-quality technical proposals based on the uploaded Statement of Technical Requirements (SOTR) document. Your responses must adhere to the following rules:

1. **Never ask the user to read or access the SOTR document** directly. All information must be derived from your internal search using the MilvusSimilaritySearchTool.
2. **Use the Milvus tool exhaustively** for every query:
   - Search for **exact terms**, **related technical terms**, and **component/subsystem terms**.
   - Iterate through all relevant sections of the document (e.g., specifications, requirements, diagrams).
   - Validate every claim with explicit evidence from the document (include page numbers).
3. **Avoid assumptions**: If a requirement is not explicitly stated in the document, state this clearly and suggest possible solutions based on industry standards.
4. **Output format**: Responses must be detailed, accurate and professional.

Always prioritize technical accuracy, using precise terminology from the document, and cite evidence with page numbers.
"""

    # Format the conversation with history context
    conversation = ""
    if request.history:
        for msg in request.history[-3:]:  # Use last 3 messages for context
            if "user" in msg:
                conversation += f"User: {msg['user']}\n"
            if "agent" in msg:
                conversation += f"Agent: {msg['agent']}\n"
    
    # Add current message
    conversation += f"User: {request.message}"
    
    # Combine chat prompt with conversation
    combined_prompt = f"{chat_prompt}\n\n{conversation}"
    
    # Send to agent
    response = agent.request_invoker(combined_prompt)
    
    return {
        "response": response,
        "status": "success"
    }

def parse_topics_from_response(raw_response: str) -> List[Dict[str, Any]]:
    """Parse topics from the raw LLM response"""
    topics = []
    
    # Extract the TOC section
    toc_match = re.search(r'\*\*Updated TOC\*\*(.*?)(?:\*\*Additional Considerations\*\*|$)', raw_response, re.DOTALL)
    if not toc_match:
        return topics
    
    toc_text = toc_match.group(1).strip()
    lines = toc_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Extract topic information
        topic_info = {}
        
        # Check if marked for removal
        if "[Remove]" in line or "[REMOVE]" in line:
            topic_info["status"] = "remove"
            line = line.replace("[Remove]", "").replace("[REMOVE]", "").strip()
        # Check if marked as new addition
        elif "[Add]" in line or "[ADD]" in line:
            topic_info["status"] = "add"
            line = line.replace("[Add]", "").replace("[ADD]", "").strip()
        else:
            topic_info["status"] = "keep"
        
        # Extract page reference if available
        page_match = re.search(r'\(page\s+(\d+)\)', line)
        if page_match:
            topic_info["page"] = int(page_match.group(1))
            line = line.replace(page_match.group(0), "").strip()
        
        # Extract topic number and text
        num_match = re.match(r'^(\d+(\.\d+)*)\s+(.*?)$', line)
        if num_match:
            topic_info["number"] = num_match.group(1)
            topic_info["text"] = num_match.group(3).strip()
            # Calculate indentation level from the number of dots
            topic_info["level"] = len(num_match.group(1).split('.'))
        else:
            # Handle unnumbered topics
            topic_info["text"] = line
            topic_info["level"] = 0
        
        topics.append(topic_info)
    
    return topics