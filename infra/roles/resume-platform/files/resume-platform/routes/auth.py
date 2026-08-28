"""Auth routes — Keycloak OIDC integration."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from services.auth import get_user_from_token
from database import Resume, get_db
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# API Secret for internal n8n callbacks
API_SECRET = os.getenv("API_SECRET", "change-me-secret")


async def require_auth(authorization: str = "Bearer ") -> dict:
    """Dependency: extract and validate Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


def require_internal_api(x_api_key: str = Header(...)) -> None:
    """Dependency: validate internal n8n API key."""
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")


@router.post("/verify")
async def verify_token(authorization: str = Header(...)):
    """Verify token and return user info."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {"valid": True, "user": user}


@router.post("/n8n/callback")
async def n8n_callback(request: Request, x_api_key: str = Header(...)):
    """Internal endpoint for n8n to push processing results."""
    # Validate internal API key
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API key")

    body = await request.json()
    resume_id = body.get("resume_id")
    action = body.get("action")  # "score" or "improve"
    data = body.get("data", {})

    if not resume_id or not action:
        raise HTTPException(status_code=400, detail="Missing resume_id or action")

    # Update resume in database
    from database import Resume
    from main import get_db
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

    return {"status": "ok", "resume_id": resume_id, "action": action}
