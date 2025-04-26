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
</style>
""" 