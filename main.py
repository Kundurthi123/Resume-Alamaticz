import uvicorn
import os

if __name__ == "__main__":
    print("==================================================")
    print(" Starting the FastAPI Application (Backend Server)")
    print("==================================================")
    
    # Change directory to backend so relative paths work
    import sys
    sys.path.pop(0)
    os.chdir("backend")
    sys.path.insert(0, os.getcwd())
    
    # Run the uvicorn server programmatically
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
