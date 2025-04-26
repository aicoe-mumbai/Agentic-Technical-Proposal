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
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"

# Model settings
MODEL_PATH = os.path.join(BASE_DIR, "models/sentence_transformer")
LLM_ENDPOINT = "http://172.16.34.235:8080"

# Create necessary directories
for directory in [PROJECTS_DIR, UPLOADS_DIR]:
    os.makedirs(directory, exist_ok=True) 