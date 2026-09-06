"""Domain models and core taxonomy helpers for media records, search plans, and pipelines."""
from __future__ import annotations

from datetime import datetime, timezone
import mimetypes
import re
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from apps.classify.taxonomy import (
    CATEGORY_LABELS,
    OCR_NOISE_BRANDS,
    OFF_MAJOR_SUBJECTS,
    SUBJECT_LABELS,
)
from apps.classify.text import fold_text

MediaType = Literal["image", "audio", "video", "other"]
IngestStatus = Literal["INDEXING", "READY", "FAILED"]
SmartCategory = Literal[
    "study",
    "pets",
    "people",
    "food",
    "receipts",
    "scenes",
    "videos",
    "other",
]


class MediaRecord(BaseModel):
    file_id: str
    filename: str
    s3_key: str
    media_type: MediaType
    content_type: str
    status: IngestStatus = "INDEXING"
    labels: List[str] = Field(default_factory=list)
    ocr_text: str = ""
    transcript: str = ""
    summary: str = ""
    category: SmartCategory = "other"
    error: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    size_bytes: int = 0
    preview_url: Optional[str] = None
    source: str = "pipeline"
    embedding: Optional[List[float]] = None
    transcribe_job_name: Optional[str] = None
    analysis_source: str = ""
    subject: str = "none"
    thumb_key: Optional[str] = None

    @field_validator("size_bytes", mode="before")
    @classmethod
    def coerce_size(cls, value):
        if value is None:
            return 0
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0


class SearchPlan(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    media_type: Optional[MediaType] = None
    category: Optional[SmartCategory] = None
    subject: Optional[str] = None
    rationale: str = ""
    vector_query: Optional[List[float]] = None
    planner_source: str = "heuristic"
    embedding_source: str = "off"
    direct_answer: Optional[str] = None
    evidence_snippet: Optional[str] = None
    source_file: Optional[str] = None

    @field_validator("media_type", "category", "subject", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if value == "" or value == "null" or value == "none":
            return None
        return value


class SearchHit(BaseModel):
    record: MediaRecord
    score: float
    vector_score: float = 0.0
    matched_on: List[str] = Field(default_factory=list)
    matched_fields: List[str] = Field(default_factory=list)


def ingest_pipeline(media_type: MediaType, analysis_source: str = "") -> List[str]:
    """Return the sequence of ingestion pipeline step descriptions for a media item."""
    steps = ["S3 PutObject"]
    source = (analysis_source or "").lower()
    if media_type == "image":
        if "rekognition" in source:
            steps += ["Rekognition DetectLabels", "Rekognition DetectText"]
        else:
            steps += ["Vision (Rekognition unavailable)"]
    elif media_type in {"audio", "video"}:
        if "transcribe" in source:
            steps += ["Amazon Transcribe vi-VN"]
        elif "indexing" in source:
            steps += ["Amazon Transcribe (waiting)"]
        else:
            steps += ["Speech (Transcribe unavailable)"]
    steps.append("DynamoDB PutItem")
    return steps


EXTENSION_OVERRIDES = {
    ".webp": "image",
    ".gif": "image",
    ".flac": "audio",
    ".m4a": "audio",
    ".mkv": "video",
    ".mov": "video",
}

for _ext, _mime in (
    (".webp", "image/webp"),
    (".gif", "image/gif"),
    (".flac", "audio/flac"),
    (".m4a", "audio/mp4"),
    (".mkv", "video/x-matroska"),
    (".mov", "video/quicktime"),
):
    mimetypes.add_type(_mime, _ext)


def infer_media_type(filename: str, content_type: str = "") -> MediaType:
    """Infer media type (image, audio, video, or other) from MIME type or file extension."""
    ctype = (content_type or "").lower()
    if "/" in ctype:
        main_type = ctype.split("/", 1)[0]
        if main_type in {"image", "audio", "video"}:
            return main_type  # type: ignore[return-value]

    guessed_type, _ = mimetypes.guess_type(filename or "")
    if guessed_type:
        main_type = guessed_type.split("/", 1)[0]
        if main_type in {"image", "audio", "video"}:
            return main_type  # type: ignore[return-value]

    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    return EXTENSION_OVERRIDES.get(ext, "other")  # type: ignore[return-value]


def infer_category(media_type: MediaType, labels: List[str], text: str, bedrock_client=None) -> SmartCategory:
    """Infer high-level taxonomy category using classification rules or Bedrock LLM."""
    from apps.classify.engine import infer_category as classify_category

    return classify_category(media_type, labels, text, bedrock_client=bedrock_client)  # type: ignore[return-value]


def infer_subject(
    labels: List[str],
    ocr_text: str,
    transcript: str,
    filename: str = "",
    bedrock_client=None,
) -> str:
    """Infer academic subject classification from labels, OCR text, transcript, and filename."""
    from apps.classify.engine import infer_subject as classify_subject

    return classify_subject(labels, ocr_text, transcript, filename, bedrock_client=bedrock_client)


def is_off_major_subject(subject: str) -> bool:
    return (subject or "") in OFF_MAJOR_SUBJECTS


def matches_subject_filter(record: MediaRecord, subject: Optional[str]) -> bool:
    if not subject:
        return True
    resolved = resolve_subject(record)
    if subject == "off_major":
        return is_off_major_subject(resolved)
    return resolved == subject


def is_noise_ocr_line(line: str) -> bool:
    """Check if an OCR text line is noise, brand artifact, or non-text garbage."""
    text = (line or "").strip()
    if len(text) < 4 or text.isdigit() or text.lower().startswith("http"):
        return True
    if re.fullmatch(r"[A-Za-z0-9]{3,10}", text) and any(ch.isdigit() for ch in text):
        return True
    folded = fold_text(text)
    if folded in OCR_NOISE_BRANDS or any(brand in folded.split() for brand in OCR_NOISE_BRANDS):
        return True
    letters = sum(ch.isalpha() for ch in text)
    return letters < 3


def usable_ocr_text(ocr_text: str) -> str:
    """Filter raw OCR output to remove noisy lines and retain only meaningful text."""
    kept: list[str] = []
    for raw in (ocr_text or "").replace(",", "\n").splitlines():
        line = raw.strip()
        if line and not is_noise_ocr_line(line):
            kept.append(line)
    return "\n".join(kept)


def has_lecture_context(record: MediaRecord) -> bool:
    """Determine whether a media record contains signals indicating academic lecture content."""
    from apps.classify.engine import has_lecture_signal

    return has_lecture_signal([*record.labels, record.ocr_text or "", record.transcript or "", record.filename])


def resolve_subject(record: MediaRecord) -> str:
    """Resolve and normalize the academic subject for a media record with fallback heuristics."""
    current = (record.subject or "none").strip()
    guessed = infer_subject(record.labels, record.ocr_text, record.transcript, record.filename)
    if guessed != "none":
        return guessed
    if current not in {"", "none", "lecture"}:
        return current
    if record.media_type == "audio" or has_lecture_context(record):
        return "lecture"
    return "none"


def record_haystack(record: MediaRecord) -> str:
    """Build a consolidated, accent-folded search text string from all record fields."""
    subject = resolve_subject(record)
    parts = [
        record.filename,
        record.media_type,
        record.category,
        CATEGORY_LABELS.get(record.category, record.category),
        subject,
        SUBJECT_LABELS.get(subject, subject),
        "ngoài ngành" if is_off_major_subject(subject) else "",
        " ".join(record.labels),
        record.ocr_text,
        record.transcript,
        record.summary,
    ]
    return fold_text(" ".join(parts))
