"""
Beauty OS — Application Entry Point

Run the FastAPI server:
    python run.py

Or with uvicorn directly:
    uvicorn backend.server:app --reload --port 8000
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
