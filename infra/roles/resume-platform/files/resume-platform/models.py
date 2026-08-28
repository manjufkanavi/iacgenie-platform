"""Pydantic v2 models for Resume Platform API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────────

class ResumeStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Request Models ─────────────────────────────────────────────────────

class ResumeUploadRequest(BaseModel):
    file_name: str
    file_size: int
    file_type: str
    job_title: Optional[str] = None
    experience_years: Optional[int] = None


class RegenerateRequest(BaseModel):
    job_title: Optional[str] = None


class ATSFeedbackRequest(BaseModel):
    """Request body for ATS scoring."""
    ocr_json: dict[str, Any]
    job_title: Optional[str] = None


class ImprovementRequest(BaseModel):
    """Request body for LLM improvement generation."""
    ocr_json: dict[str, Any]
    ats_score: dict[str, Any]
    job_title: Optional[str] = None


# ── Response Models ────────────────────────────────────────────────────

class ATSScore(BaseModel):
    overall: int = Field(ge=0, le=100)
    keywords_match: int = Field(ge=0, le=100)
    formatting: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    section_scores: dict[str, int] = Field(default_factory=dict)
    missing_keywords: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ResumeImprovement(BaseModel):
    rewritten_sections: dict[str, str] = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)
    keyword_suggestions: list[str] = Field(default_factory=list)
    formatting_tips: list[str] = Field(default_factory=list)
    ats_score_after: Optional[int] = None


class ResumeResult(BaseModel):
    id: str
    user_id: str
    filename: str
    ocr_json: dict[str, Any] = Field(default_factory=dict)
    ats_score: Optional[ATSScore] = None
    improvements: Optional[ResumeImprovement] = None
    status: ResumeStatus
    job_title: Optional[str] = None
    experience_years: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    resume_id: str
    status: ResumeStatus
    message: str


class ScoreResponse(BaseModel):
    ats_score: ATSScore


class ImprovementResponse(BaseModel):
    improvements: ResumeImprovement


class ListResumeItem(BaseModel):
    id: str
    filename: str
    status: ResumeStatus
    job_title: Optional[str] = None
    created_at: datetime


class ListResumesResponse(BaseModel):
    resumes: list[ListResumeItem]
    total: int


class DeleteResponse(BaseModel):
    message: str
    deleted: bool


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
