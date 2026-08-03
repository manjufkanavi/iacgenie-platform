# config/cors.py

import os

# List of allowed origins for CORS (Cross-Origin Resource Sharing)

# Add frontend domains here to allow them to access the backend API.

# Allow specific application domains via environment variable, with a strict fallback
# In production, this should be set via the CORS_ORIGINS environment variable

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", os.getenv("ALLOWED_ORIGINS", "https://app.iacgenie.com")
    ).split(",")
    if origin.strip()
]
