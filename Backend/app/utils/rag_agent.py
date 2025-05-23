import logging
from langchain.agents import initialize_agent
from langchain.tools import Tool, StructuredTool
from typing import Dict, List, Any, Optional, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.llms import HuggingFaceEndpoint
from langchain.callbacks import StdOutCallbackHandler
from Backend.app.core.config import GEMINI_API_KEY
from Backend.app.utils.vector_utils import process_query
from Backend.app.utils.pdf_utils import extract_text_from_pdf


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# endpoint = "http://172.16.34.235:8080"

class RAGAgent:
    """RAG Agent for querying the database using LangChain"""
    
    def __init__(self, pdf_path: str, data_dict: Dict[str, str]):
        self.pdf_path = pdf_path
        self.data_dict = data_dict
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            convert_system_message_to_human=True,
            api_key=GEMINI_API_KEY
        )
        # self.llm = HuggingFaceEndpoint(endpoint_url = endpoint)
        self.agent = None
        self.callbacks = [StdOutCallbackHandler()]
        logger.info(f"Initializing RAG agent for {pdf_path}")
        self.initialize_agent()

    def initialize_agent(self):
        """Initialize the LangChain agent pipeline"""
        logger.info("Creating tools for agent")
        tools = self._create_tools()
        
        logger.info("Initializing agent with tools")
        self.agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent="structured-chat-zero-shot-react-description",
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=150,
            callbacks=self.callbacks
        )

    def _create_tools(self) -> List[Tool]:
        """Create list of tools for the LangChain agent"""
        def similarity_search(
            query: str,
            start_idx: Optional[int] = 1,
            end_idx: Optional[int] = 3
        ) -> str:
            """Perform similarity search with range"""
            return process_query(
                query,
                result_range=(max(0, start_idx-1), min(end_idx, start_idx+2))
            )

        return [
            StructuredTool.from_function(
                func=similarity_search,
                name="MilvusSimilaritySearchTool",
                description=(
                    "This tool performs a fast similarity search within the database using the provided query text.\n"
                    "Parameters:\n"
                    "- query: The text to search for (required)\n"
                    "- start_idx: Starting index for results (optional, default=1)\n"
                    "- end_idx: Ending index for results (optional, default=3)\n"
                    "Note: Will return maximum 3 results regardless of range specified.\n"
                    "Use this tool to find relevant sections from the document that contain scope information."
                ),
            ),
            Tool(
                name="PDFPageExtractorTool",
                func=lambda page_range: extract_text_from_pdf(self.pdf_path, page_range),
                description=(
                    "This tool extracts text from specific pages of the PDF.\n"
                    "Parameter: page_range (string in format 'start-end', e.g., '3-5').\n"
                    "Use when you need to analyze specific pages directly."
                ),
            )
        ]

    def extract_scope(self) -> Dict[str, Any]:
        """Extract scope information using the agent"""
        logger.info("Starting scope extraction")
        scope_prompt = scope_prompt = """
            Analyze the document thoroughly and extract ALL scope-related information. Follow these steps:

            1. Core Scope Identification:
            - Find sections labeled as 'Scope', 'Project Scope', 'Scope of Work', or similar
            - Include any referenced sections, paragraphs, or appendices mentioned within the scope

            2. Detailed Scope Elements:
            a) Project Inclusions:
                - List all deliverables with their specified quantities
                - Identify any hardware, software, or system components
                - Note any specific versions, models, or specifications mentioned
                
            b) Project Timeline and Milestones:
                - Extract any dates, durations, or deadlines
                - Note project phases or stage-wise deliverables
                - Include any schedule-related constraints
                - Look for dependencies between deliverables

            c) Requirements and Specifications:
                - Technical requirements and standards
                - Performance criteria or KPIs
                - Compliance requirements or certifications needed
                - Integration requirements with other systems
                - When a requirement references another section, ALWAYS fetch and include that section's content

            d) Project Boundaries:
                - Explicit exclusions from scope
                - Limitations or constraints
                - Dependencies on other projects or systems
                - Assumptions and prerequisites

            3. Supporting Information:
            - Referenced documents or standards
            - Related specifications or requirements
            - Any clarifications or additional context provided
            - Important notes or caveats mentioned
            
            4. Quantitative Information:
            - Numbers of units/components required
            - Performance metrics or targets
            - Budget constraints if mentioned
            - Resource allocations
            - Extract ALL numerical specifications and requirements

            5. Track Information Sources:
            - For EACH extracted piece of information, INCLUDE the page number where it was found
            - Note section numbers or references
            - Document any cross-referenced sections consulted
            - Build a complete trace of information flow between sections

            6. Cross-Reference Resolution:
            - For EACH reference to another section/paragraph:
                1. Use MilvusSimilaritySearchTool to get the referenced content and if needed get the entire page using PDFPageExtractorTool
                2. Analyze the new content for additional scope information
                3. If the new content has more references, follow those as well
                4. Maintain a clear connection between related pieces of information
                5. Capture and indicate the page number for all extracted referenced content

            7. Output Formatting:
            - Structure the output clearly with headers and subsections
            - For each extracted point, clearly indicate:
                - The extracted information
                - The corresponding page number(s)
            - Example Format:
                [Page X] <Extracted Information>

            8. Handling Missing Information:
            - If certain scope elements are not found, explicitly state what information is missing

            IMPORTANT: Always follow references to their source and include the complete context.
            When you see phrases like "refer to", "as per", "as defined in", "according to section",
            make sure to fetch and analyze those referenced sections to provide complete information.

            Remember to validate that all requirements are properly captured, and no critical information is missed. Deliver only the final result to user.
            Strictly adhere to the output format
            Page: []
            Scope Retrieved:[]
            """

        try:
            logger.info("Invoking agent with enhanced scope prompt")
            result = self.agent.invoke({"input": scope_prompt})
            output = result.get("output", "")
            logger.info(f"Agent completed with output length: {len(output)}")
            
            # Extract page numbers from the agent's analysis
            source_pages = []
            for tool_use in result.get("intermediate_steps", []):
                logger.info(f"Tool use: {tool_use}")
                if "page" in str(tool_use):
                    try:
                        page_num = int(str(tool_use).split("page")[1].split()[0])
                        if page_num not in source_pages:
                            source_pages.append(page_num)
                    except:
                        continue
            
            return {
                "scope_text": output,
                "source_pages": sorted(source_pages),
                "is_complete": bool(output.strip())
            }
        except Exception as e:
            logger.error(f"Error in scope extraction: {str(e)}", exc_info=True)
            return {
                "scope_text": f"Error extracting scope: {str(e)}",
                "source_pages": [],
                "is_complete": False
            }

    
    def request_invoker(self, topic_prompt) -> Dict[str, Any]:
        """Generate topics using the agent"""
        logger.info("Starting topic generation")
         
        result = self.agent.invoke({"input": topic_prompt})
        output = result.get("output", "")
        logger.info(f"Agent completed with output length: {len(output)}")
        return output
            