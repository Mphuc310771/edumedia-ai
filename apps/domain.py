from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
import re
from typing import List, Literal, Optional
import unicodedata

from pydantic import BaseModel, Field, field_validator

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

    @field_validator("size_bytes", mode="before")
    @classmethod
    def coerce_size(cls, value):
        if value is None:
            return 0
        return int(value)


class SearchPlan(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    media_type: Optional[MediaType] = None
    category: Optional[SmartCategory] = None
    rationale: str = ""
    vector_query: Optional[List[float]] = None

    @field_validator("media_type", "category", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if value == "" or value == "null":
            return None
        return value


class SearchHit(BaseModel):
    record: MediaRecord
    score: float
    vector_score: float = 0.0
    matched_on: List[str] = Field(default_factory=list)
    matched_fields: List[str] = Field(default_factory=list)


def ingest_pipeline(media_type: MediaType) -> List[str]:
    prefix = ["S3 PutObject", "SQS ingest queue"]
    if media_type == "image":
        return prefix + ["Rekognition DetectLabels", "Rekognition DetectText", "DynamoDB PutItem"]
    if media_type in {"audio", "video"}:
        return prefix + ["Amazon Transcribe vi-VN", "DynamoDB PutItem"]
    return prefix + ["DynamoDB PutItem"]


def infer_media_type(filename: str, content_type: str) -> MediaType:
    name = filename.lower()
    ctype = (content_type or "").lower()
    if ctype.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
        return "image"
    if ctype.startswith("audio/") or name.endswith((".mp3", ".wav", ".m4a", ".flac")):
        return "audio"
    if ctype.startswith("video/") or name.endswith((".mp4", ".mov", ".avi", ".mkv")):
        return "video"
    return "other"


CATEGORY_KEYWORDS: dict[SmartCategory, tuple[tuple[str, int], ...]] = {
    "receipts": (
        ("receipt", 5), ("invoice", 5), ("hóa đơn", 5), ("biên lai", 5), ("bill", 4),
        ("vat", 4), ("phiếu", 4), ("vnd", 4), ("tổng tiền", 5), ("thanh toán", 4),
        ("payment", 4), ("cash", 3), ("tax", 4), ("total", 4), ("tiền", 3),
    ),
    "pets": (
        ("pet", 5), ("dog", 5), ("cat", 5), ("canine", 5), ("feline", 5),
        ("tiger", 5), ("lion", 5), ("bird", 5), ("chó", 5), ("mèo", 5),
        ("thú cưng", 5), ("động vật", 4), ("hổ", 5), ("báo", 5), ("chim", 4),
        ("fish", 4), ("cá", 4), ("animal", 3), ("mammal", 3), ("wildlife", 4),
        ("zoo", 3), ("fauna", 3),
    ),
    "people": (
        ("person", 4), ("human", 4), ("face", 4), ("portrait", 5), ("athlete", 5),
        ("player", 4), ("soccer", 4), ("football", 4), ("sport", 3), ("man", 3),
        ("woman", 3), ("boy", 3), ("girl", 3), ("crowd", 3), ("people", 4),
        ("celebrity", 5), ("ronaldo", 5), ("người", 4), ("cầu thủ", 5),
        ("chân dung", 5), ("khuôn mặt", 4), ("selfie", 5), ("head", 2),
    ),
    "study": (
        ("whiteboard", 5), ("blackboard", 5), ("lecture", 5), ("slide", 4),
        ("toán", 5), ("bài tập", 5), ("giảng đường", 5), ("giải tích", 5),
        ("aws", 4), ("code", 4), ("document", 4), ("paper", 3), ("school", 4),
        ("student", 4), ("university", 4), ("bảng", 4), ("học", 4), ("sách", 4),
        ("book", 4), ("diagram", 4), ("text", 2), ("screenshot", 3),
    ),
    "food": (
        ("food", 5), ("dish", 5), ("meal", 5), ("drink", 4), ("beverage", 4),
        ("coffee", 5), ("tea", 4), ("burger", 5), ("pizza", 5), ("restaurant", 4),
        ("cà phê", 5), ("món ăn", 5), ("đồ ăn", 5), ("ẩm thực", 5), ("trà sữa", 5),
        ("bánh", 4), ("nước uống", 4),
    ),
    "scenes": (
        ("landscape", 5), ("mountain", 5), ("beach", 5), ("sunset", 5),
        ("sunrise", 5), ("ocean", 5), ("sea", 4), ("nature", 3), ("sky", 2),
        ("city", 4), ("building", 4), ("street", 4), ("biển", 5), ("núi", 5),
        ("hoàng hôn", 5), ("phố", 4), ("phong cảnh", 5), ("du lịch", 4),
        ("travel", 4), ("outdoors", 3), ("architecture", 4),
    ),
}


def infer_category(media_type: MediaType, labels: List[str], text: str) -> SmartCategory:
    if media_type == "video":
        return "videos"
    if media_type == "audio":
        return "study"

    blob = " ".join([*labels, text]).lower()
    folded_blob = fold_text(blob)

    scores: dict[SmartCategory, int] = {cat: 0 for cat in CATEGORY_KEYWORDS}

    for category, kw_weights in CATEGORY_KEYWORDS.items():
        for kw, weight in kw_weights:
            folded_kw = fold_text(kw)
            if folded_kw in folded_blob or kw in blob:
                scores[category] += weight

    best_cat, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score >= 3:
        return best_cat
    return "other"


CATEGORY_LABELS = {
    "study": "Học tập & Giảng đường",
    "pets": "Thú cưng & Động vật",
    "people": "Con người & Chân dung",
    "food": "Ẩm thực & Đồ uống",
    "receipts": "Hóa đơn & Biên lai",
    "scenes": "Cảnh quan & Du lịch",
    "videos": "Video & Kỷ niệm",
    "other": "Khác",
}


def fold_text(value: str) -> str:
    """Lowercase and strip Vietnamese diacritics so 'cho' matches 'chó'."""
    normalized = unicodedata.normalize("NFD", value or "")
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return stripped.lower()


def record_haystack(record: MediaRecord) -> str:
    parts = [
        record.filename,
        record.media_type,
        record.category,
        CATEGORY_LABELS.get(record.category, record.category),
        " ".join(record.labels),
        record.ocr_text,
        record.transcript,
        record.summary,
    ]
    return fold_text(" ".join(parts))
