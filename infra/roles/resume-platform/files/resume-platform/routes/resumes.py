"""Resume routes — CRUD, upload, scoring, improvements."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func

from database import Resume, User, get_db
from models import (
    ResumeResult,
    UploadResponse,
    ScoreResponse,
    ImprovementResponse,
    ListResumesResponse,
    DeleteResponse,
    ListResumeItem,
    ResumeStatus,
)
from services.ocr import extract_text_from_file, parse_text_to_json
from services.ats import calculate_ats_score
from services.llm import generate_improvements
from services.minio import upload_file, delete_file, download_file
from services.auth import get_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/resume", tags=["resumes"])

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024


async def require_auth(authorization: str = "Bearer ") -> dict:
    """Dependency: extract and validate Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


@router.post("/upload", response_model=UploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    job_title: str = Form(None),
    experience_years: int = Form(None),
    user: dict = Depends(require_auth),
):
    """Upload a resume file for processing."""
    # Validate file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

    # Validate file type
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/png",
        "image/jpeg",
        "image/jpg",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: PDF, DOCX, JPG, PNG")

    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_filename = file.filename or "resume"
    safe_filename = f"{file_id}_{original_filename}"

    # Upload to MinIO
    try:
        minio_key = upload_file(file_content, safe_filename, file.content_type)
    except Exception as e:
        logger.error(f"MinIO upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

    # Create resume record
    async with get_db() as db:
        # Get or create user
        result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = result.scalar_one_or_none()

        if not db_user:
            db_user = User(
                id=uuid.uuid4(),
                keycloak_id=user.get("keycloak_id"),
                email=user.get("email"),
                name=user.get("name"),
            )
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

        resume = Resume(
            user_id=db_user.id,
            filename=original_filename,
            file_type=file.content_type,
            file_size=len(file_content),
            minio_key=minio_key,
            status=ResumeStatus.PROCESSING,
            job_title=job_title,
            experience_years=experience_years,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

    return UploadResponse(
        resume_id=str(resume.id),
        status=ResumeStatus.PROCESSING,
        message="Resume uploaded successfully. Processing started.",
    )


@router.get("/", response_model=ListResumesResponse)
async def list_resumes(
    user: dict = Depends(require_auth),
):
    """List all resumes for the authenticated user."""
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = result.scalar_one_or_none()

        if not db_user:
            return ListResumesResponse(resumes=[], total=0)

        resumes_result = await db.execute(
            select(Resume)
            .where(Resume.user_id == db_user.id)
            .order_by(Resume.created_at.desc())
        )
        resumes = resumes_result.scalars().all()

        items = [
            ListResumeItem(
                id=str(r.id),
                filename=r.filename,
                status=ResumeStatus(r.status),
                job_title=r.job_title,
                created_at=r.created_at,
            )
            for r in resumes
        ]

    return ListResumesResponse(resumes=items, total=len(items))


@router.get("/{resume_id}", response_model=ResumeResult)
async def get_resume(
    resume_id: str,
    user: dict = Depends(require_auth),
):
    """Get resume details including OCR, ATS score, and improvements."""
    async with get_db() as db:
        result = await db.execute(
            select(Resume).where(Resume.id == resume_id)
        )
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        # Verify ownership
        user_result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = user_result.scalar_one_or_none()
        if not db_user or resume.user_id != db_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return ResumeResult(
            id=str(resume.id),
            user_id=str(resume.user_id),
            filename=resume.filename,
            ocr_json=resume.ocr_json or {},
            ats_score=resume.ats_score_json if resume.ats_score_json else None,
            improvements=resume.improvements_json if resume.improvements_json else None,
            status=ResumeStatus(resume.status),
            job_title=resume.job_title,
            experience_years=resume.experience_years,
            created_at=resume.created_at,
            updated_at=resume.updated_at,
        )


@router.post("/{resume_id}/regenerate")
async def regenerate_pipeline(
    resume_id: str,
    user: dict = Depends(require_auth),
):
    """Re-run the full pipeline: OCR → ATS Score → LLM Improvements."""
    async with get_db() as db:
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        # Verify ownership
        user_result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = user_result.scalar_one_or_none()
        if not db_user or resume.user_id != db_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Download file from MinIO
        try:
            file_bytes = download_file(resume.minio_key)
        except Exception as e:
            logger.error(f"MinIO download failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to download file")

        # Step 1: OCR
        logger.info(f"Running OCR on resume {resume_id}")
        text = extract_text_from_file(file_bytes, resume.file_type)
        ocr_json = parse_text_to_json(text)
        resume.ocr_json = ocr_json
        resume.status = ResumeStatus.PROCESSING
        await db.commit()

        # Step 2: ATS Score
        logger.info(f"Calculating ATS score for resume {resume_id}")
        ats_score = calculate_ats_score(ocr_json, resume.job_title)
        resume.ats_score_json = ats_score
        await db.commit()

        # Step 3: LLM Improvements
        logger.info(f"Generating improvements for resume {resume_id}")
        improvements = generate_improvements(ocr_json, ats_score, resume.job_title)
        resume.improvements_json = improvements
        resume.status = ResumeStatus.COMPLETED
        await db.commit()

    return {
        "status": "completed",
        "resume_id": resume_id,
        "ats_score": ats_score,
        "improvements": improvements,
    }


@router.delete("/{resume_id}", response_model=DeleteResponse)
async def delete_resume(
    resume_id: str,
    user: dict = Depends(require_auth),
):
    """Delete a resume and its file."""
    async with get_db() as db:
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        # Verify ownership
        user_result = await db.execute(
            select(User).where(User.keycloak_id == user.get("keycloak_id"))
        )
        db_user = user_result.scalar_one_or_none()
        if not db_user or resume.user_id != db_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete from MinIO
        try:
            delete_file(resume.minio_key)
        except Exception as e:
            logger.warning(f"MinIO delete warning: {e}")

        # Delete from database
        await db.delete(resume)
        await db.commit()

    return DeleteResponse(message="Resume deleted successfully", deleted=True)
