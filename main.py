import os
import sys
import uvicorn

# Ensure the root directory is in the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the FastAPI app instance so deployment platforms can discover it
from backend.main import app

if __name__ == "__main__":
    print("==================================================")
    print(" Starting the FastAPI Application (Backend Server)")
    print("==================================================")
    
    # Run the uvicorn server programmatically
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
