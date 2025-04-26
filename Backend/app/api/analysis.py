from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, List, Optional, Any
import os
import re

from Backend.app.models.models import (
    TopicGenerationResponse, ContentGenerationRequest, 
    ContentGenerationResponse, ChatRequest, ChatResponse
)
from Backend.app.utils.rag_agent import RAGAgent
from Backend.app.db.database import get_template_by_name
from Backend.app.core.config import UPLOADS_DIR
from Backend.app.api.documents import active_documents

router = APIRouter(prefix="/analysis", tags=["analysis"])

# Store active RAG agents
active_agents = {}

def get_agent(document_name: str, template_name: str):
    """Get or create a RAG agent for a document and template"""
    doc_path = os.path.join(UPLOADS_DIR, document_name)
    
    if not os.path.exists(doc_path):
        raise HTTPException(status_code=404, detail=f"Document {document_name} not found")
    
    doc_id = os.path.basename(doc_path)
    if doc_id not in active_documents or active_documents[doc_id]["status"] != "processed":
        raise HTTPException(status_code=400, detail="Document has not been processed")
    
    # Get template data
    template = get_template_by_name(template_name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_name} not found")
    
    # Get template data dictionary
    file_path = template.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Template file not found")
    
    # Check if agent exists, create if not
    agent_key = f"{doc_id}_{template_name}"
    if agent_key not in active_agents:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path)
            ws = wb['Sheet1']
            data_dict = {}
            for i in range(2, ws.max_row + 1):
                key = ws.cell(i, 1).value
                value = ws.cell(i, 2).value
                if key is not None and value is not None:
                    data_dict[key] = value
                    
            # Create agent
            active_agents[agent_key] = RAGAgent(doc_path, data_dict)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating RAG agent: {str(e)}")
    
    return active_agents[agent_key]

@router.post("/generate-topics/{document_name}/{template_name}", response_model=TopicGenerationResponse)
async def generate_topics(document_name: str, template_name: str):
    """Generate topics based on document scope and template"""
    agent = get_agent(document_name, template_name)
    
    # Get scope data
    doc_id = os.path.basename(os.path.join(UPLOADS_DIR, document_name))
    if "scope" not in active_documents.get(doc_id, {}):
        raise HTTPException(status_code=400, detail="Document scope has not been extracted")
    
    scope_data = active_documents[doc_id]["scope"]
    
    # Get template TOC
    template = get_template_by_name(template_name)
    given_toc = template.get("project_TOC", "")
    
    # Generate topic prompt
    topic_prompt = f"""
Develop a hierarchical Table of Contents (ToC) by validating the content of the uploaded Statement of Technical Requirements (SOTR) document against the provided Example ToC.

Table of Contents (ToC):
{given_toc}

### Scope Information:
{scope_data.get('scope_text', 'No scope available')}
(Found on pages: {', '.join(map(str, scope_data.get('source_pages', [])))})

### Instructions:
1. For each item in the ToC:
   - Search for the exact term, related technical terms, and component/subsystem terms using MilvusSimilaritySearchTool.
   - Document evidence found or indicate absence.
   - Never assume the presence of topic unless it is itertaed to check with the tool.
2. Decision Criteria:
   - Keep items with clear evidence.
   - Mark items for removal if evidence is missing.
   - Highlight any new additions found in the SOTR.
3. Required Output:
   Provide the updated ToC as plain text (preserving the hierarchy) and annotate items needing removal with [REMOVE] and new additions with [ADD]. Include page numbers where evidence is found.
4. Process:
   - Process every item.
   - Skip common sections (e.g., Preamble, Introduction, Scope, Delivery) without search.
   - Show search attempts for each item.
   - Skip searching for items having keep as like in the TOC.

### Important:
Perform exact search over the topics word to word search and it should be available in the exact page you refer.
Your output should strictly adhere to the following output format:
Sample Output:
**Updated TOC**
1. Preamble
2. Introduction
3. IPMS (page 7)
    3.1 Propulsion system (page 8)
    3.2 Alarm system [Remove]
    ...
**Additional Considerations**
1) Evidences
2) Why some topics removed
3) Annotations..
"""

    # Send to agent
    result = agent.analyze_query(topic_prompt)
    
    # Process the result to extract topics
    raw_response = result.get("output", "")
    
    # Parse the raw response to extract structured topics
    topics = parse_topics_from_response(raw_response)
    
    return {
        "topics": topics,
        "raw_response": raw_response
    }

@router.post("/generate-content/{document_name}/{template_name}", response_model=ContentGenerationResponse)
async def generate_content(
    document_name: str, 
    template_name: str, 
    request: ContentGenerationRequest
):
    """Generate content for a specific topic"""
    agent = get_agent(document_name, template_name)
    
    # Get scope data
    doc_id = os.path.basename(os.path.join(UPLOADS_DIR, document_name))
    if "scope" not in active_documents.get(doc_id, {}):
        raise HTTPException(status_code=400, detail="Document scope has not been extracted")
    
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
"""

    # User input for the agent
    user_input = f"User Selected Topic: {request.topic}"
    
    # Create the combined prompt
    combined_prompt = f"{content_prompt}\n\n{user_input}"
    
    # Send to agent
    result = agent.analyze_query(combined_prompt)
    content = result.get("output", "")
    
    return {
        "content": content,
        "topic": request.topic
    }

@router.post("/chat/{document_name}/{template_name}", response_model=ChatResponse)
async def chat_with_document(
    document_name: str, 
    template_name: str, 
    request: ChatRequest
):
    """Chat with the document using the RAG agent"""
    agent = get_agent(document_name, template_name)
    
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
    result = agent.analyze_query(combined_prompt)
    response = result.get("output", "")
    
    return {
        "response": response,
        "status": result.get("status", "success")
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