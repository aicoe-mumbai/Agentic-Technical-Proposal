import os

# API Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
API_V1_PATH = "/api/v1"

# App Configuration
APP_TITLE = "Technical Proposal Generator"
APP_DESCRIPTION = "Generate technical proposals from SOTR documents"

# Streamlit configuration
WIDE_MODE = True
ENABLE_THEME = True
CUSTOM_CSS = """
<style>
.main-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
}

.topics-container {
    max-height: 600px;
    overflow-y: auto;
    border: 1px solid #ddd;
    padding: 1rem;
    border-radius: 5px;
}

.topic-item {
    padding: 8px;
    margin-bottom: 4px;
    border-radius: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.topic-item.remove {
    background-color: #ffebee;
    text-decoration: line-through;
    color: #b71c1c;
}

.topic-item.add {
    background-color: #e8f5e9;
    color: #1b5e20;
    font-weight: bold;
}

.chat-message {
    padding: 8px;
    border-radius: 5px;
    margin-bottom: 4px;
}

.user-message {
    background-color: #e0f7fa;
}

.agent-message {
    background-color: #f1f8e9;
}

.editor-canvas {
    border: 1px solid #ddd;
    min-height: 500px;
    padding: 1rem;
    border-radius: 5px;
    background-color: white;
}

.document-canvas {
    border: 1px solid #ddd;
    padding: 2rem;
    margin: 1rem 0;
    border-radius: 5px;
    background-color: white;
    min-height: 800px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.document-canvas h1, .document-canvas h2, .document-canvas h3, .document-canvas h4 {
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    font-weight: bold;
}

.document-canvas h1 {
    font-size: 1.8rem;
    text-align: center;
    border-bottom: 1px solid #eee;
    padding-bottom: 1rem;
}

.document-canvas h2 {
    font-size: 1.5rem;
    border-bottom: 1px solid #f0f0f0;
    padding-bottom: 0.5rem;
}

.document-canvas h3 {
    font-size: 1.3rem;
}

.document-canvas h4 {
    font-size: 1.1rem;
}

.document-canvas p {
    margin-bottom: 1rem;
    line-height: 1.6;
    text-align: justify;
}

.document-canvas ul, .document-canvas ol {
    margin-bottom: 1rem;
    padding-left: 2rem;
}

.document-canvas li {
    margin-bottom: 0.5rem;
    line-height: 1.5;
}

.document-canvas strong {
    font-weight: bold;
}

.document-canvas em {
    font-style: italic;
}

.right-sidebar, .left-sidebar {
    position: fixed;
    height: 100vh;
    width: 300px;
    top: 0;
    padding: 1rem;
    background-color: #f5f5f5;
    overflow-y: auto;
}

.left-sidebar {
    left: 0;
    border-right: 1px solid #ddd;
}

.right-sidebar {
    right: 0;
    border-left: 1px solid #ddd;
}

.main-container {
    margin-left: 320px;
    margin-right: 320px;
}

@media (max-width: 1200px) {
    .main-container {
        margin-left: 20px;
        margin-right: 20px;
    }
    
    .right-sidebar, .left-sidebar {
        position: relative;
        width: 100%;
        height: auto;
    }
}

@media print {
    .document-canvas {
        border: none;
        box-shadow: none;
        padding: 0;
    }
}
</style>
""" 