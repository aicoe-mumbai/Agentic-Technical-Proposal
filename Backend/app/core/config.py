import os
from pathlib import Path

# API settings
API_V1_STR = "/api/v1"
PROJECT_NAME = "Technical Proposal Generator API"

# File storage paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
PROJECTS_DIR = os.path.join(BASE_DIR, "project_templates")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

# Database settings
DB_FILE = os.path.join(BASE_DIR, "project_templates.db")

# Milvus settings
MILVUS_HOST = "4.188.67.129"
MILVUS_PORT = "19530"

# Model settings
MODEL_PATH = os.path.join(BASE_DIR, "models/sentence_transformer")
# LLM_ENDPOINT = "http://localhost:8080" # Remove or comment out
GEMINI_API_KEY = "AIzaSyD63fdWAO6j5ByW7Wajq3uEZ6TEA9L0ic4" # Add Gemini Key

# Create necessary directories
for directory in [PROJECTS_DIR, UPLOADS_DIR]:
    os.makedirs(directory, exist_ok=True) 