from langchain.agents import initialize_agent
from langchain.tools import Tool
from langchain.llms import HuggingFaceEndpoint
from typing import Dict, List, Optional, Any

from Backend.app.core.config import LLM_ENDPOINT
from Backend.app.utils.vector_utils import process_query, get_best_match_value
from Backend.app.utils.pdf_utils import extract_text_from_pdf

class RAGAgent:
    """
    RAG Agent for querying the database using LangChain
    """
    def __init__(self, pdf_path: str, data_dict: Dict[str, str]):
        """
        Initializes the RAGAgent
        
        Args:
            pdf_path: Path to the uploaded PDF file
            data_dict: Dictionary containing predefined template data
        """
        self.pdf_path = pdf_path
        self.data_dict = data_dict
        self.llm = HuggingFaceEndpoint(endpoint_url=LLM_ENDPOINT, max_new_tokens=2048)
        self.agent = None
        self.initialize_agent()

    def initialize_agent(self):
        """Initialize the LangChain agent pipeline"""
        self.agent = initialize_agent_pipeline(self.llm, self.pdf_path, self.data_dict)
                
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a query using the agent pipeline
        
        Args:
            query: The query string to analyze
            
        Returns:
            Dictionary containing the output and any additional information
        """
        try:
            result = self.agent.invoke(query)
            return {"output": result.get("output", ""), "status": "success"}
        except Exception as e:
            return {"output": f"Error processing query: {str(e)}", "status": "error"}

def create_tools(pdf_path: str, data_dict: Dict[str, str]) -> List[Tool]:
    """
    Create the list of tools for the LangChain agent
    
    Args:
        pdf_path: Path to the uploaded PDF file
        data_dict: Dictionary containing predefined templates
        
    Returns:
        List of Tool objects
    """
    return [
        Tool(
            name="MilvusSimilaritySearchTool",
            func=lambda query: process_query(query),
            description=(
                "This tool performs a fast similarity search within the database using the provided query text. "
                "Use this tool to find relevant sections from the uploaded document that match the user's query."
            ),
        ),
        Tool(
            name="MilvusRangeSearchTool",
            func=lambda query, start_idx=0, end_idx=3: process_query(query, result_range=(int(start_idx), int(end_idx))),
            description=(
                "This tool performs a similarity search with custom result range. "
                "Parameters: query (string), start_idx (int), end_idx (int). "
                "Use this for more targeted, paginated results."
            ),
        ),
        Tool(
            name="PDFPageExtractorTool",
            func=lambda page_range: extract_text_from_pdf(pdf_path, page_range),
            description=(
                "This tool extracts text from specific pages of the PDF. "
                "Parameter: page_range (string in format 'start-end', e.g., '3-5'). "
                "Use when you need to analyze specific pages directly."
            ),
        ),
        Tool(
            name="ContentGenerationTemplateTool",
            func=lambda topic: get_best_match_value(topic, data_dict=data_dict),
            description=(
                "This tool generates content for a given topic by retrieving the best-matching predefined template. "
                "Use when the user selects a topic and requests detailed content generation."
            ),
        )
    ]

def initialize_agent_pipeline(llm, pdf_path: str, data_dict: Dict[str, str]):
    """
    Initialize the LangChain agent pipeline
    
    Args:
        llm: The language model instance
        pdf_path: Path to the uploaded PDF file
        data_dict: Dictionary containing predefined templates
        
    Returns:
        Initialized LangChain agent
    """
    tools = create_tools(pdf_path, data_dict)
    return initialize_agent(
        tools=tools,
        llm=llm,
        agent="structured-chat-zero-shot-react-description",
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=150,
    ) 