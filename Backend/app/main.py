from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from Backend.app.core.config import API_V1_STR, PROJECT_NAME
from Backend.app.api import templates, documents, analysis

# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    description="Backend API for Technical Proposal Generator",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific frontends
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(templates.router, prefix=API_V1_STR)
app.include_router(documents.router, prefix=API_V1_STR)
app.include_router(analysis.router, prefix=API_V1_STR)

@app.get("/")
async def root():
    """Root endpoint to check API status"""
    return {
        "message": "Technical Proposal Generator API is running",
        "status": "ok",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 