from __future__ import annotations

import logging
import os
from typing import Optional

from apps.aws.providers import get_runtime
from apps.domain import MediaRecord, infer_category, infer_media_type

logger = logging.getLogger(__name__)

IMAGE_FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}
AUDIO_FORMATS = {".mp3": "mp3", ".wav": "wav", ".m4a": "mp4", ".flac": "flac"}
VIDEO_FORMATS = {".mp4": "mp4", ".mov": "mp4"}


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
    if record.ocr_text:
        first = record.ocr_text.strip().splitlines()[0][:180]
        return f"OCR: {first}"
    if record.transcript:
        return f"Transcript: {record.transcript[:180]}"
    if record.labels:
        return f"Labels: {', '.join(record.labels[:8])}"
    return f"Indexed file {record.filename}"
