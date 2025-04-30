from pymilvus import connections, Collection, utility
from sentence_transformers import SentenceTransformer
from fuzzywuzzy import fuzz
from typing import Dict, List, Tuple, Optional, Union, Any
from langchain_core.documents import Document
from langchain_community.vectorstores import Milvus
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
import os

from Backend.app.core.config import MILVUS_HOST, MILVUS_PORT, MODEL_PATH
from Backend.app.core.state import active_documents

# Search parameters for Milvus
search_params = {"metric_type": "L2", "params": {"ef": 100}}

def get_embedding_model():
    """Get the sentence transformer embedding model"""
    try:
        return SentenceTransformer(MODEL_PATH)
    except Exception as e:
        # Fallback to HuggingFace embeddings via LangChain
        return HuggingFaceEmbeddings(model_name=MODEL_PATH)

def get_collection_name_for_document(doc_id: str) -> str:
    """Generate a unique collection name for a document"""
    # Remove file extension and special characters that might cause issues in Milvus
    clean_id = os.path.splitext(doc_id)[0]
    clean_id = ''.join(c if c.isalnum() else '_' for c in clean_id)
    return f"doc_{clean_id}"

def process_query(
    user_input: str, 
    collection_name: str = "DEC", 
    result_range: Tuple[int, int] = (1, 3),
    doc_id: str = None
) -> str:
    """
    Process query against Milvus vector database and return results
    
    Args:
        user_input: User's query string
        collection_name: Name of the Milvus collection to search (legacy parameter)
        result_range: Tuple of (start_index, end_index) to slice results. Will return max 3 results.
        doc_id: Document ID to search in its specific collection
        
    Returns:
        Formatted string with search results
    """
    # Connect to Milvus server
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    
    # If doc_id is provided, use document-specific collection
    if doc_id:
        collection_name = get_collection_name_for_document(doc_id)

    # Ensure result range doesn't exceed 3 results
    start_idx, end_idx = result_range
    end_idx = min(end_idx, start_idx + 2)  # Limit to max 3 results from start

    # Check if the collection exists
    try:
        if not utility.has_collection(collection_name):
            return f"Error: Collection '{collection_name}' not found. Ensure the document has been processed correctly."
        
        collection = Collection(collection_name)
    except Exception as e:
        return f"Error: Collection '{collection_name}' not found. Ensure the collection exists and the name is correct. Error: {str(e)}"

    # Load the collection
    try:
        collection.load()
    except Exception as e:
        return f"Error loading collection: {str(e)}"

    # Check if the necessary fields exist
    schema_fields = [field.name for field in collection.schema.fields]
    required_fields = ["vector", "text"]
    missing_fields = [field for field in required_fields if field not in schema_fields]

    if missing_fields:
        return f"Error: Missing required fields in collection schema: {', '.join(missing_fields)}"

    # Generate embedding vector from the user input
    try:
        embedding_model = get_embedding_model()
        query_vector = embedding_model.encode([user_input]).tolist()
    except Exception as e:
        return f"Error generating embedding vector: {str(e)}"
    
    # No filtering expression by default
    expr = None

    try:
        search_results = collection.search(
            data=query_vector,
            anns_field="vector",
            param=search_params,
            limit=10,  # Reduced from 50 since we only need max 3
            output_fields=["text"],
            consistency_level="Strong",
            expr=expr
        )
    except Exception as e:
        return f"Error during search: {str(e)}"

    # Extract and format the search results
    all_hits = []
    for hits in search_results:
        all_hits.extend(hits)
    
    # Apply the result range with 3-result limit
    sliced_hits = all_hits[start_idx:end_idx]

    if not sliced_hits:
        return "No results found for the given query and filters."

    context = '\n---\n'.join(
        f"Text:</b> {hit.entity.get('text')}"
        for hit in sliced_hits
    )
    return context

def get_best_match_value(input_string: str, data_dict: Dict[str, str], threshold: float = 0.8) -> str:
    """
    Find the best matching value from a dictionary using fuzzy matching
    
    Args:
        input_string: The input string to match
        data_dict: Dictionary of key-value pairs to match against
        threshold: Threshold score (0-1) for accepting a match
        
    Returns:
        The best matching value or a default message
    """
    best_value = None
    highest_score = 0
    for key, value in data_dict.items():
        score = fuzz.ratio(input_string.lower(), key.lower())
        if score > highest_score:
            highest_score = score
            best_value = value
    if highest_score >= threshold * 100:
        return best_value
    else:
        return "No Template found for this topic."

def initialize_vector_db(documents: List[Document], collection_name: str = None) -> bool:
    """
    Initialize the vector database with documents
    
    Args:
        documents: List of Document objects to store
        collection_name: Explicit collection name (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get document ID from first document's source
        doc_id = os.path.basename(documents[0].metadata["source"])
        
        # Generate collection name from document ID if not explicitly provided
        if not collection_name:
            collection_name = get_collection_name_for_document(doc_id)
        
        # Update status to show vector DB initialization
        if doc_id in active_documents:
            active_documents[doc_id].update({
                "status": "processing",
                "message": "Initializing vector database",
                "progress": 90,  # Text extraction is complete at this point
                "collection_name": collection_name  # Store collection name for future queries
            })
        
        # Drop collection if it exists
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
        
        # Create new collection with document
        embeddings = HuggingFaceEmbeddings(model_name=MODEL_PATH)
        Milvus.from_documents(
            documents, 
            embeddings, 
            collection_name=collection_name,
            drop_old=True, 
            connection_args={"uri": f"http://{MILVUS_HOST}:{MILVUS_PORT}"}
        )
        
        # Update status to show completion
        if doc_id in active_documents:
            active_documents[doc_id].update({
                "status": "processed",
                "message": "Document processed successfully",
                "progress": 100,
                "collection_name": collection_name
            })
            
        return True
    except Exception as e:
        print(f"Error initializing vector database: {str(e)}")
        return False