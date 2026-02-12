"""
Beauty OS — Application Entry Point

Run the FastAPI server:
    python run.py

Or with uvicorn directly:
    uvicorn backend.server:app --reload --port 8000
"""

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=port,
    )
