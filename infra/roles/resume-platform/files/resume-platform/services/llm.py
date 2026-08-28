"""Ollama LLM service — Qwen 0.5B for resume improvement generation."""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ── Prompt Templates ───────────────────────────────────────────────────

IMPROVEMENT_PROMPT = """You are an expert resume reviewer and improvement specialist.

Given the following resume content (extracted via OCR) and ATS score analysis,
provide specific, actionable improvements.

## Resume Content
{resume_content}

## ATS Score Analysis
{ats_analysis}

## Job Title (optional)
{job_title}

## Instructions
Analyze the resume and provide:
1. **Rewritten sections**: Improve weak sections with better phrasing, action verbs, and quantification
2. **Suggestions**: General advice for improvement
3. **Keyword suggestions**: Missing keywords that should be added
4. **Formatting tips**: Suggestions for better formatting

Return your response as a JSON object with these exact keys:
- "rewritten_sections": object mapping section names to improved text
- "suggestions": array of string suggestions
- "keyword_suggestions": array of string keyword suggestions
- "formatting_tips": array of string formatting tips
- "estimated_ats_score_after": integer (estimated score after improvements)

Be specific and actionable. Do NOT include any text outside the JSON object.
"""


def generate_improvements(
    ocr_json: dict[str, Any],
    ats_score: dict[str, Any],
    job_title: str | None = None,
) -> dict[str, Any]:
    """Call Ollama to generate resume improvements."""
    # Build resume content string
    sections = ocr_json.get("sections", {})
    content_parts: list[str] = []
    for section_name, section_text in sections.items():
        if section_text:
            content_parts.append(f"=== {section_name.upper()} ===\n{section_text}")

    resume_content = "\n\n".join(content_parts) if content_parts else ocr_json.get("raw_text", "No content extracted")

    # Build ATS analysis string
    ats_str = json.dumps(ats_score, indent=2)

    # Build prompt
    prompt = IMPROVEMENT_PROMPT.format(
        resume_content=resume_content[:4000],  # Truncate to avoid token limits
        ats_analysis=ats_str,
        job_title=job_title or "Not specified",
    )

    # Call Ollama
    try:
        response = requests.post(
            f"{_get_ollama_url()}/api/generate",
            json={
                "model": _get_ollama_model(),
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "max_tokens": 2048,
                },
            },
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()
        raw_output = result.get("response", "")

        # Parse JSON from response
        return _parse_llm_response(raw_output)

    except requests.exceptions.ConnectionError:
        logger.error("Ollama connection failed — returning fallback improvements")
        return _get_fallback_improvements(ats_score)
    except Exception as e:
        logger.error(f"Ollama LLM call failed: {e}")
        return _get_fallback_improvements(ats_score)


def _parse_llm_response(raw: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    # Strip markdown code blocks if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last line (```json and ```)
        if len(lines) > 2:
            cleaned = "\n".join(lines[1:-1])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM response is not valid JSON, using fallback")
        return _get_fallback_improvements({})


def _get_fallback_improvements(ats_score: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic fallback improvements when LLM is unavailable."""
    overall = ats_score.get("overall", 0)
    recs = ats_score.get("recommendations", [])

    rewritten: dict[str, str] = {}
    suggestions: list[str] = list(recs) if recs else [
        "Add a professional summary at the top",
        "Use action verbs to describe achievements",
        "Quantify your accomplishments with numbers and percentages",
    ]

    if overall < 50:
        rewritten["summary"] = "Add a 2-3 line professional summary highlighting your key skills and experience."
        suggestions.append("Your resume needs significant improvement — consider adding more detail to each section")

    return {
        "rewritten_sections": rewritten,
        "suggestions": suggestions,
        "keyword_suggestions": [],
        "formatting_tips": [
            "Use consistent formatting throughout",
            "Include bullet points for readability",
            "Keep font size between 10-12pt",
        ],
        "estimated_ats_score_after": min(100, overall + 15),
    }


def _get_ollama_url() -> str:
    import os
    return os.getenv("OLLAMA_URL", "http://ollama:11434")


def _get_ollama_model() -> str:
    import os
    return os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
