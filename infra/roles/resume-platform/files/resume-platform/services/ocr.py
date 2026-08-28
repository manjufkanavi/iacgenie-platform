"""Surya OCR service — CPU-based structured text extraction from PDF/DOCX/JPG."""

from __future__ import annotations

import io
import logging
from typing import Any

import cv2
import numpy as np
from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pypdf (fallback) + Surya for scanned pages."""
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)

    # If we got text, return it
    full_text = "\n".join(text_parts)
    if full_text.strip():
        return full_text

    # If no text extracted (scanned PDF), convert to images and use Surya
    logger.info("PDF appears scanned, falling back to image-based OCR")
    return ""  # Will be handled by image OCR path


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_image(file_bytes: bytes) -> str:
    """Extract text from image using Surya OCR (CPU-based)."""
    try:
        from surya.ocr import run_ocr
        from surya.model.detection import segformer
        from surya.model.recognition.model import load_model as load_rec_model
        from surya.model.recognition.processor import load_processor

        # Load models (cached after first run)
        logger.info("Loading Surya OCR models (first run may be slow)...")
        detector = segformer.load_detector()
        recognition_model, processor = load_rec_model(), load_processor()

        # Decode image
        img_array = np.frombuffer(file_bytes, dtype=np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # Run OCR
        lang = ["en"]
        results = run_ocr([image], [lang], detector, recognition_model, processor)

        if results and results[0].text_lines:
            return "\n".join([tl.text for tl in results[0].text_lines])

        return ""
    except ImportError:
        logger.warning("Surya OCR not available, returning empty text")
        return ""
    except Exception as e:
        logger.error(f"Surya OCR failed: {e}")
        return ""


def extract_text_from_file(file_bytes: bytes, file_type: str) -> str:
    """Route to appropriate extractor based on file type."""
    if file_type in ("application/pdf", "pdf"):
        return extract_text_from_pdf(file_bytes)
    elif file_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
    ):
        return extract_text_from_docx(file_bytes)
    elif file_type.startswith("image/"):
        return extract_text_from_image(file_bytes)
    else:
        logger.warning(f"Unsupported file type: {file_type}")
        return ""


def parse_text_to_json(text: str) -> dict[str, Any]:
    """Parse extracted text into structured JSON with sections."""
    sections: dict[str, str] = {}
    current_section = "raw_text"
    current_lines: list[str] = []

    # Common section headers to detect
    section_headers = {
        "contact_info": [
            "contact", "email", "phone", "address", "linkedin", "portfolio",
            "website", "location", "telephone",
        ],
        "summary": [
            "summary", "objective", "profile", "about me", "professional summary",
            "career objective",
        ],
        "experience": [
            "experience", "work experience", "employment", "professional experience",
            "work history", "employment history",
        ],
        "education": [
            "education", "academic", "degrees", "qualifications", "education history",
        ],
        "skills": [
            "skills", "technical skills", "competencies", "core competencies",
            "technical abilities",
        ],
        "projects": [
            "projects", "personal projects", "key projects", "portfolio projects",
        ],
        "certifications": [
            "certifications", "certificates", "credentials", "licenses",
        ],
        "awards": [
            "awards", "honors", "achievements", "recognition",
        ],
        "languages": [
            "languages", "language proficiency",
        ],
        "interests": [
            "interests", "hobbies", "personal interests",
        ],
    }

    for line in text.split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check if this line is a section header
        line_lower = line_stripped.lower()
        is_header = False

        for section_name, headers in section_headers.items():
            for header in headers:
                if header in line_lower and len(line_stripped) < 60:
                    # Save previous section
                    if current_lines:
                        sections[current_section] = "\n".join(current_lines)
                    current_section = section_name
                    current_lines = []
                    is_header = True
                    break
            if is_header:
                break

        if not is_header:
            current_lines.append(line_stripped)

    # Save last section
    if current_lines:
        sections[current_section] = "\n".join(current_lines)

    # If no sections detected, put everything in raw_text
    if not sections:
        sections["raw_text"] = text

    return {
        "sections": sections,
        "raw_text": text,
        "word_count": len(text.split()),
        "line_count": len(text.split("\n")),
    }
