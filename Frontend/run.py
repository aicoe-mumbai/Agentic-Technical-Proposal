import streamlit.web.cli as stcli
import os
import sys

# Add the root directory to system path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root_dir)

if __name__ == '__main__':
    # Get the path to the Streamlit app
    app_path = os.path.join(os.path.dirname(__file__), "app/main.py")
    
    # Set environment variables
    os.environ["API_BASE_URL"] = os.environ.get("API_BASE_URL", "http://localhost:8000")
    
    # Run the Streamlit app
    sys.argv = ["streamlit", "run", app_path, "--server.port=8501", "--server.headless=true"]
    sys.exit(stcli.main()) 