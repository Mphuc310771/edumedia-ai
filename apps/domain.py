from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional
import unicodedata

from pydantic import BaseModel, Field, field_validator

MediaType = Literal["image", "audio", "video", "other"]
IngestStatus = Literal["INDEXING", "READY", "FAILED"]
SmartCategory = Literal[
    "study",
    "pets",
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

    @field_validator("media_type", "category", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if value == "" or value == "null":
            return None
        return value


class SearchHit(BaseModel):
    record: MediaRecord
    score: float
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


def infer_category(media_type: MediaType, labels: List[str], text: str) -> SmartCategory:
    if media_type == "video":
        return "videos"
    blob = " ".join([*labels, text]).lower()
    if any(token in blob for token in ("receipt", "invoice", "hóa đơn", "biên lai", "bill", "vat", "phiếu", "vnd")):
        return "receipts"
    if any(token in blob for token in ("dog", "cat", "pet", "animal", "chó", "mèo", "lion", "sư tử")):
        return "pets"
    if any(token in blob for token in ("food", "coffee", "cup", "burger", "cà phê", "giày", "shoe")):
        return "food"
    if any(token in blob for token in ("beach", "city", "mountain", "sunset", "biển", "phố", "cảnh")):
        return "scenes"
    if any(
        token in blob
        for token in (
            "text",
            "whiteboard",
            "blackboard",
            "document",
            "lecture",
            "aws",
            "toán",
            "bảng",
            "slide",
            "study",
        )
    ):
        return "study"
    return "other"


CATEGORY_LABELS = {
    "study": "Học tập & Giảng đường",
    "pets": "Thú cưng & Động vật",
    "food": "Ăn uống & Đồ vật",
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


def record_haystack(record: "MediaRecord") -> str:
    return fold_text(
        " ".join(
            [
                record.filename,
                " ".join(record.labels),
                record.ocr_text,
                record.transcript,
                record.summary,
            ]
        )
    )
