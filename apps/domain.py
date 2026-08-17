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
    "study": (
        ("computer", 6), ("laptop", 6), ("pc", 6), ("monitor", 6), ("screen", 5),
        ("electronics", 5), ("desk", 5), ("keyboard", 5), ("mouse", 4), ("shelf", 4),
        ("bookcase", 4), ("books", 5), ("notebook", 5), ("whiteboard", 6),
        ("blackboard", 6), ("lecture", 6), ("slide", 5), ("toán", 6),
        ("bài tập", 6), ("giảng đường", 6), ("giải tích", 6), ("aws", 5),
        ("code", 5), ("document", 4), ("paper", 4), ("school", 5),
        ("student", 5), ("university", 5), ("máy tính", 6), ("bàn học", 6),
        ("bàn làm việc", 6), ("bảng", 5), ("học", 5), ("sách", 5),
        ("book", 5), ("diagram", 5), ("screenshot", 4),
    ),
    "receipts": (
        ("receipt", 6), ("invoice", 6), ("hóa đơn", 6), ("biên lai", 6), ("bill", 5),
        ("vat", 5), ("phiếu", 4), ("vnd", 5), ("tổng tiền", 6), ("thanh toán", 5),
        ("payment", 5), ("cash", 4), ("tax", 4), ("total", 4), ("tiền", 3),
    ),
    "pets": (
        ("pet", 6), ("dog", 6), ("cat", 6), ("canine", 6), ("feline", 6),
        ("tiger", 6), ("lion", 6), ("bird", 6), ("chó", 6), ("mèo", 6),
        ("thú cưng", 6), ("động vật", 5), ("hổ", 6), ("báo", 6), ("chim", 5),
        ("fish", 5), ("cá", 5), ("animal", 4), ("mammal", 4), ("wildlife", 5),
        ("zoo", 4), ("fauna", 4),
    ),
    "people": (
        ("person", 5), ("human", 5), ("face", 5), ("portrait", 6), ("athlete", 6),
        ("player", 5), ("soccer", 5), ("football", 5), ("sport", 4), ("man", 4),
        ("woman", 4), ("boy", 4), ("girl", 4), ("crowd", 4), ("people", 5),
        ("celebrity", 6), ("ronaldo", 6), ("người", 5), ("cầu thủ", 6),
        ("chân dung", 6), ("khuôn mặt", 5), ("selfie", 6),
    ),
    "food": (
        ("food", 6), ("dish", 6), ("meal", 6), ("drink", 5), ("beverage", 5),
        ("coffee", 6), ("tea", 5), ("burger", 6), ("pizza", 6), ("restaurant", 5),
        ("cà phê", 6), ("món ăn", 6), ("đồ ăn", 6), ("ẩm thực", 6), ("trà sữa", 6),
        ("bánh", 4), ("nước uống", 5),
    ),
    "scenes": (
        ("landscape", 6), ("mountain", 6), ("beach", 6), ("sunset", 6),
        ("sunrise", 6), ("ocean", 6), ("sea", 5), ("nature", 4),
        ("city", 5), ("building", 4), ("street", 4), ("biển", 6), ("núi", 6),
        ("hoàng hôn", 6), ("phố", 4), ("phong cảnh", 6), ("du lịch", 5),
        ("travel", 5), ("outdoors", 4), ("architecture", 4),
    ),
}


def _matches_keyword(kw: str, raw_blob: str, folded_blob: str) -> bool:
    """Exact whole-word or phrase matching to prevent false substring matches (e.g. 'man' in 'command')."""
    kw_clean = kw.strip().lower()
    folded_kw = fold_text(kw_clean)
    if " " in kw_clean:
        return kw_clean in raw_blob or folded_kw in folded_blob
    pattern = rf"\b{re.escape(folded_kw)}\b"
    return bool(re.search(pattern, folded_blob, re.IGNORECASE))


def infer_category(media_type: MediaType, labels: List[str], text: str) -> SmartCategory:
    if media_type == "video":
        return "videos"
    if media_type == "audio":
        return "study"

    # Prioritize Rekognition Vision labels first (they are cleaner than OCR noise)
    labels_text = " ".join(labels).lower()
    folded_labels = fold_text(labels_text)

    # Full blob including OCR
    full_blob = f"{labels_text} {text}".lower()
    folded_full = fold_text(full_blob)

    scores: dict[SmartCategory, int] = {cat: 0 for cat in CATEGORY_KEYWORDS}

    for category, kw_weights in CATEGORY_KEYWORDS.items():
        for kw, weight in kw_weights:
            # Matches in labels get 1.5x weight because visual labels are high confidence
            if _matches_keyword(kw, labels_text, folded_labels):
                scores[category] += int(weight * 1.5)
            elif _matches_keyword(kw, full_blob, folded_full):
                scores[category] += weight

    best_cat, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score >= 4:
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
