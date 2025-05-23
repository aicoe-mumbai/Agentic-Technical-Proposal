import uvicorn
import os
import sys

# Add the root directory to system path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root_dir)

if __name__ == "__main__":
    # Run the FastAPI application
    uvicorn.run("Backend.app.main:app", host="0.0.0.0", port=8001, reload=True) 