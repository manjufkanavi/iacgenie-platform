#!/usr/bin/env python3

"""

Iacgenie AI Backend Startup Script

This script starts the FastAPI server with proper configuration.

"""

import sys

import os

from pathlib import Path

# Add the workspace root directory to Python path (contains middleware module)

workspace_root = Path(__file__).parent.parent

sys.path.insert(0, str(workspace_root))

# Add the backend directory to Python path (for backend modules)

backend_dir = Path(__file__).parent

sys.path.insert(0, str(backend_dir))

# Set environment variables

os.environ.setdefault("PYTHONPATH", str(backend_dir))

print("🚀 Starting Iacgenie AI Backend...")

print("📍 Server will run on http://0.0.0.0:8000")

print("🔧 Debug mode: enabled")

# Check API keys

mistral_api_key = os.getenv("MISTRAL_API_KEY")

gemini_api_key = os.getenv("GEMINI_API_KEY")

if mistral_api_key:
    print("🤖 Mistral API: configured")
else:
    print("🤖 Mistral API: not configured")
if gemini_api_key:
    print("🤖 Gemini API: configured")
else:
    print("🤖 Gemini API: not configured")
# Import and run the FastAPI app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
