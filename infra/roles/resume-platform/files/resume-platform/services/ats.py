"""Deterministic ATS scoring engine — keyword matching, formatting, completeness."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Common action verbs for resume analysis ────────────────────────────

ACTION_VERBS = {
    "achieved", "accomplished", "administered", "built", "collaborated",
    "created", "developed", "designed", "delivered", "implemented",
    "improved", "increased", "managed", "led", "launched", "optimized",
    "reduced", "resolved", "streamlined", "spearheaded", "supervised",
    "trained", "wrote", "engineered", "architected", "deployed",
    "automated", "mentored", "negotiated", "analyzed", "evaluated",
    "established", "executed", "facilitated", "generated", "initiated",
    "negotiated", "orchestrated", "produced", "restructured", "transformed",
}

# ── Common resume section keywords ─────────────────────────────────────

REQUIRED_SECTIONS = {
    "contact_info": ["email", "phone", "linkedin", "address", "location"],
    "summary": ["summary", "objective", "profile", "about"],
    "experience": ["experience", "work", "employment", "history"],
    "education": ["education", "degree", "university", "college", "bachelor", "master"],
    "skills": ["skills", "technical", "competencies", "abilities"],
}

# ── Common resume formatting indicators ────────────────────────────────

BULLET_PATTERNS = [r"^\s*[-•*]\s+", r"^\s*\d+\.\s+"]


def calculate_ats_score(ocr_json: dict[str, Any], job_title: str | None = None) -> dict[str, Any]:
    """Calculate deterministic ATS score from OCR-extracted resume JSON.

    Scoring breakdown:
    - Keywords match: 30% (if job_title provided)
    - Formatting: 25% (bullet points, structure, readability)
    - Completeness: 30% (required sections present)
    - Section quality: 15% (action verbs, quantification)
    """
    sections = ocr_json.get("sections", {})
    raw_text = ocr_json.get("raw_text", "")
    word_count = ocr_json.get("word_count", 0)

    # ── 1. Completeness Score (30%) ────────────────────────────────────
    completeness_score = _calculate_completeness(sections)

    # ── 2. Formatting Score (25%) ──────────────────────────────────────
    formatting_score = _calculate_formatting(raw_text, sections)

    # ── 3. Keyword Match Score (30%) ───────────────────────────────────
    keyword_score, missing_keywords = _calculate_keyword_match(raw_text, job_title)

    # ── 4. Section Quality Score (15%) ─────────────────────────────────
    quality_score = _calculate_section_quality(raw_text, sections)

    # ── Overall Score ──────────────────────────────────────────────────
    overall = int(
        keyword_score * 0.30
        + formatting_score * 0.25
        + completeness_score * 0.30
        + quality_score * 0.15
    )

    # ── Recommendations ────────────────────────────────────────────────
    recommendations = _generate_recommendations(
        completeness_score, formatting_score, keyword_score, quality_score,
        missing_keywords, word_count,
    )

    # ── Section Scores ─────────────────────────────────────────────────
    section_scores = {}
    for section_name in REQUIRED_SECTIONS:
        if section_name in sections:
            section_scores[section_name] = 100
        else:
            section_scores[section_name] = 0

    return {
        "overall": overall,
        "keywords_match": keyword_score,
        "formatting": formatting_score,
        "completeness": completeness_score,
        "section_scores": section_scores,
        "missing_keywords": missing_keywords[:20],  # Top 20
        "recommendations": recommendations,
    }


def _calculate_completeness(sections: dict[str, str]) -> int:
    """Score how many required sections are present."""
    present = 0
    total = len(REQUIRED_SECTIONS)

    for section_name, keywords in REQUIRED_SECTIONS.items():
        text = sections.get(section_name, "").lower()
        if any(kw in text for kw in keywords):
            present += 1

    return int((present / total) * 100) if total > 0 else 0


def _calculate_formatting(raw_text: str, sections: dict[str, str]) -> int:
    """Score resume formatting quality."""
    score = 100
    issues = []

    # Check for bullet points in experience
    experience = sections.get("experience", "")
    if experience:
        bullet_count = len(re.findall(r"^\s*[-•*]\s+", experience, re.MULTILINE))
        if bullet_count == 0:
            score -= 30
            issues.append("No bullet points found in experience section")
        elif bullet_count < 3:
            score -= 10
            issues.append("Few bullet points in experience section")

    # Check for proper spacing
    lines = raw_text.split("\n")
    empty_lines = sum(1 for line in lines if not line.strip())
    if empty_lines < len(lines) * 0.05 and len(lines) > 10:
        score -= 10
        issues.append("Poor spacing between sections")

    # Check for consistent formatting (all caps headers)
    all_caps_lines = [
        line for line in lines
        if line.strip() and line.strip().isupper() and len(line.strip()) < 50
    ]
    if len(all_caps_lines) < 2:
        score -= 5

    # Check word count
    word_count = len(raw_text.split())
    if word_count < 100:
        score -= 20
        issues.append("Resume too short (less than 100 words)")
    elif word_count > 1000:
        score -= 10
        issues.append("Resume too long (more than 1000 words)")

    return max(0, min(100, score))


def _calculate_keyword_match(raw_text: str, job_title: str | None) -> tuple[int, list[str]]:
    """Score keyword match against job title/industry terms."""
    if not job_title:
        return 50, []  # Neutral score if no job title provided

    raw_lower = raw_text.lower()
    job_words = set(re.findall(r"\b\w+\b", job_title.lower()))

    # Industry-specific keyword pools
    industry_keywords = {
        "software": ["python", "java", "javascript", "react", "api", "database",
                      "sql", "git", "docker", "kubernetes", "aws", "azure", "testing",
                      "agile", "scrum", "ci/cd", "linux", "algorithm", "data structure"],
        "data": ["python", "sql", "machine learning", "deep learning", "pandas",
                 "numpy", "tensorflow", "pytorch", "statistics", "visualization",
                 "etl", "data pipeline", "spark", "hadoop", "airflow"],
        "devops": ["docker", "kubernetes", "terraform", "ansible", "aws", "azure",
                   "ci/cd", "jenkins", "monitoring", "linux", "scripting", "automation"],
        "design": ["figma", "ui", "ux", "wireframe", "prototype", "user research",
                   "design system", "accessibility", "responsive", "css", "html"],
        "marketing": ["seo", "sem", "content", "analytics", "google analytics",
                      "social media", "email marketing", "conversion", "a/b testing"],
        "finance": ["financial analysis", "forecasting", "budgeting", "excel",
                    "financial modeling", "risk", "compliance", "accounting"],
    }

    # Find best matching industry
    matched_industries = []
    for industry, keywords in industry_keywords.items():
        if any(kw in job_title.lower() for kw in keywords):
            matched_industries.append(industry)

    # If no industry match, use job title words directly
    if not matched_industries:
        target_keywords = list(job_words)
    else:
        target_keywords = []
        for industry in matched_industries:
            target_keywords.extend(industry_keywords[industry])

    # Remove common words
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
                  "for", "of", "with", "by", "is", "are", "was", "were", "be", "been"}
    target_keywords = [kw for kw in target_keywords if kw not in stop_words]

    # Count matches
    matched = [kw for kw in target_keywords if kw in raw_lower]
    missing = [kw for kw in target_keywords if kw not in raw_lower]

    if not target_keywords:
        return 50, []

    score = int((len(matched) / len(target_keywords)) * 100)
    return min(score, 100), missing


def _calculate_section_quality(raw_text: str, sections: dict[str, str]) -> int:
    """Score quality of resume sections."""
    score = 100

    # Check for action verbs
    experience = sections.get("experience", "").lower()
    action_count = sum(1 for verb in ACTION_VERBS if verb in experience)
    if action_count < 3:
        score -= 25
    elif action_count < 6:
        score -= 10

    # Check for quantification (numbers, percentages)
    numbers = re.findall(r"\d+%", raw_text)
    if not numbers:
        score -= 15

    # Check for dates in experience
    date_pattern = re.findall(r"\d{4}[-–/]\d{2}[-–/]\d{2}", raw_text)
    if not date_pattern:
        score -= 10

    return max(0, score)


def _generate_recommendations(
    completeness: int, formatting: int, keyword: int,
    quality: int, missing_keywords: list[str], word_count: int,
) -> list[str]:
    """Generate actionable recommendations based on scores."""
    recs: list[str] = []

    if completeness < 60:
        recs.append("Add missing sections: contact info, summary, experience, education, skills")
    if formatting < 60:
        recs.append("Use bullet points and proper spacing for better readability")
    if keyword < 50:
        recs.append(f"Include more industry keywords: {', '.join(missing_keywords[:5])}")
    if quality < 60:
        recs.append("Use more action verbs and quantify achievements with numbers")
    if word_count < 100:
        recs.append("Expand your resume — aim for at least 100 words")
    if word_count > 1000:
        recs.append("Condense your resume — keep it concise and relevant")

    # Always add positive reinforcement
    if completeness >= 80:
        recs.append("Great section coverage — your resume has all key components")
    if formatting >= 80:
        recs.append("Well-formatted resume with good structure")

    return recs
