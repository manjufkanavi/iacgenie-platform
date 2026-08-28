"""Resume Platform API — FastAPI application."""

from __future__ import annotations

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Logging ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── App ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Resume Platform API",
    description="AI-powered resume review, ATS scoring, and improvement platform",
    version="1.0.0",
)

# ── CORS ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "https://resume.iacgenie.com").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────────────────

from routes import auth, resumes, internal

app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(internal.router)


# ── Health Check ────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from datetime import datetime, timezone

    return JSONResponse(content={
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ── Startup ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize database tables on startup."""
    from database import Base, engine

    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")


# ── Shutdown ────────────────────────────────────────────────────────────

@app.on_event("shutdown")
async def shutdown():
    """Close database connections on shutdown."""
    logger.info("Shutting down...")
