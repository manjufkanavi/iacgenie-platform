"""Internal routes — n8n callbacks and health checks."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])

API_SECRET = os.getenv("API_SECRET", "change-me-secret")


def require_internal_api(x_api_key: str = Header(...)) -> None:
    """Dependency: validate internal n8n API key."""
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")


@router.post("/n8n/process-resume")
async def n8n_process_resume(request: Request, x_api_key: str = Header(...)):
    """Internal endpoint: n8n triggers full pipeline processing."""
    require_internal_api(x_api_key)

    body = await request.json()
    resume_id = body.get("resume_id")
    action = body.get("action")  # "score" or "improve"
    data = body.get("data", {})

    if not resume_id or not action:
        raise HTTPException(status_code=400, detail="Missing resume_id or action")

    from database import Resume, get_db
    from sqlalchemy import select

    async with get_db() as db:
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        if action == "score":
            resume.ats_score_json = data
            resume.status = "completed"
        elif action == "improve":
            resume.improvements_json = data
            resume.status = "completed"

        await db.commit()

    return JSONResponse(content={"status": "ok", "resume_id": resume_id, "action": action})


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
