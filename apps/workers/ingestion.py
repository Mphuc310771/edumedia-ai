from __future__ import annotations

import logging
import os
import re
from typing import Optional

from apps.aws.providers import get_runtime
from apps.domain import CATEGORY_LABELS, MediaRecord, infer_category, infer_media_type

logger = logging.getLogger(__name__)

IMAGE_FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}
AUDIO_FORMATS = {".mp3": "mp3", ".wav": "wav", ".m4a": "mp4", ".flac": "flac"}
VIDEO_FORMATS = {".mp4": "mp4", ".mov": "mp4"}

LABEL_TRANSLATIONS = {
    "computer": "Máy tính",
    "laptop": "Laptop",
    "electronics": "Thiết bị điện tử",
    "pc": "PC",
    "monitor": "Màn hình",
    "screen": "Màn hình hiển thị",
    "desk": "Bàn làm việc",
    "keyboard": "Bàn phím",
    "shelf": "Kệ sách",
    "bookcase": "Giá sách",
    "person": "Người",
    "human": "Con người",
    "face": "Gương mặt",
    "head": "Khuôn mặt",
    "portrait": "Chân dung",
    "athlete": "Vận động viên",
    "player": "Cầu thủ",
    "soccer": "Bóng đá",
    "animal": "Động vật",
    "pet": "Thú cưng",
    "dog": "Chó",
    "cat": "Mèo",
    "tiger": "Hổ",
    "lion": "Sư tử",
    "bird": "Chim",
    "fish": "Cá",
    "landscape": "Phong cảnh",
    "nature": "Thiên nhiên",
    "beach": "Bãi biển",
    "mountain": "Núi non",
    "sunset": "Hoàng hôn",
    "city": "Đô thị",
    "building": "Tòa nhà",
    "street": "Đường phố",
    "food": "Món ăn",
    "drink": "Đồ uống",
    "coffee": "Cà phê",
    "tea": "Trà",
    "receipt": "Hóa đơn",
    "invoice": "Biên lai",
    "whiteboard": "Bảng viết",
    "document": "Tài liệu",
    "paper": "Giấy tờ",
}


def _clean_ocr_snippet(ocr_text: str) -> str:
    """Extract a clean, readable text snippet from OCR, filtering out noisy symbols."""
    lines = [line.strip() for line in (ocr_text or "").splitlines() if line.strip()]
    meaningful = [l for l in lines if not l.startswith("http") and len(l) > 2]
    if meaningful:
        combined = " • ".join(meaningful[:3])
        return combined[:100]
    return ""


def ingest_object(file_id: str, object_key: str, filename: Optional[str] = None, content_type: str = "") -> MediaRecord:
    runtime = get_runtime()
    name = filename or os.path.basename(object_key)
    media_type = infer_media_type(name, content_type)
    record = MediaRecord(
        file_id=file_id,
        filename=name,
        s3_key=object_key,
        media_type=media_type,
        content_type=content_type or "application/octet-stream",
        status="INDEXING",
        source="pipeline",
    )
    runtime.catalog.put(record)

    try:
        ext = os.path.splitext(name)[1].lower()
        labels: list[str] = []
        ocr = ""
        transcript = ""

        if media_type == "image":
            try:
                labels, ocr = runtime.vision.analyze_image(object_key, name)
            except Exception as exc:
                logger.warning("Vision analysis error on %s: %s", name, exc)
                labels = ["Image", "Photo"]
                ocr = ""
        elif media_type in {"audio", "video"}:
            try:
                media_format = {**AUDIO_FORMATS, **VIDEO_FORMATS}.get(ext, "mp4")
                transcript = runtime.speech.transcribe(object_key, media_format)
                labels = ["Speech", "Audio"] if transcript else ["Media"]
            except Exception as exc:
                logger.warning("Speech analysis error on %s: %s", name, exc)
                transcript = f"Bản ghi đa phương tiện: {name}"
                labels = ["Audio"]
        else:
            labels = ["Document"]

        blob = " ".join([*labels, ocr, transcript, name])
        record.labels = labels
        record.ocr_text = ocr
        record.transcript = transcript
        record.category = infer_category(media_type, labels, blob)
        record.summary = _build_summary(record)
        record.status = "READY"
        record.error = None
        runtime.catalog.put(record)
        runtime.metrics.emit("MediaIngested", 1)
        logger.info(
            "ingest_ready file_id=%s type=%s labels=%s provider=%s",
            file_id,
            media_type,
            len(labels),
            runtime.provider,
        )
        return record
    except Exception as exc:
        logger.exception("ingest_failed file_id=%s", file_id)
        record.status = "FAILED"
        record.error = str(exc)
        runtime.catalog.put(record)
        runtime.metrics.emit("MediaIngestFailed", 1)
        raise


def _build_summary(record: MediaRecord) -> str:
    category_name = CATEGORY_LABELS.get(record.category, record.category)

    if record.media_type == "audio":
        ext = os.path.splitext(record.filename)[1].upper().replace(".", "")
        size_str = f"{record.size_bytes / (1024 * 1024):.1f} MB" if record.size_bytes > 0 else ""
        if record.transcript and not record.transcript.startswith("Bản ghi đa phương tiện"):
            return f"Bản ghi âm thanh ({ext}, {size_str}): \"{record.transcript[:120]}...\""
        return f"File ghi âm giọng nói {ext} ({size_str}) đã lưu trữ an toàn trên Amazon S3 và lập chỉ mục trong danh mục {category_name}."

    if record.media_type == "video":
        ext = os.path.splitext(record.filename)[1].upper().replace(".", "")
        size_str = f"{record.size_bytes / (1024 * 1024):.1f} MB" if record.size_bytes > 0 else ""
        return f"Video đa phương tiện {ext} ({size_str}) được lập chỉ mục trong danh mục {category_name}."

    # Image summary synthesis
    translated_labels = [LABEL_TRANSLATIONS.get(l.lower(), l) for l in record.labels[:5]]
    labels_str = ", ".join(translated_labels) if translated_labels else ""
    ocr_snippet = _clean_ocr_snippet(record.ocr_text)

    if labels_str and ocr_snippet:
        return f"Ảnh chứa: {labels_str}. Phát hiện văn bản: \"{ocr_snippet}\", phân loại vào danh mục {category_name}."
    if labels_str:
        return f"Ảnh được Amazon Rekognition nhận diện đặc trưng: {labels_str}, phân loại vào danh mục {category_name}."
    if ocr_snippet:
        return f"Văn bản trích xuất: \"{ocr_snippet}\", phân loại vào danh mục {category_name}."

    return f"Tài liệu {record.filename} đã được phân loại vào danh mục {category_name}."
