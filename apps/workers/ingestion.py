"""Media ingestion and analysis pipeline worker.

Pipeline flow:
    1. S3 Storage: Ingest raw media objects uploaded to Amazon S3.
    2. Vision / Speech Analysis:
       - Images: Amazon Rekognition (DetectLabels, DetectText) + JPEG thumbnail generation.
       - Audio/Video: Amazon Transcribe (Vietnamese speech-to-text transcription).
    3. Classification & Categorization: Heuristic rule-based and Bedrock LLM taxonomy classification.
    4. Vector Embedding: Amazon Titan Text Embeddings v2 (256-d output; native default 1024-d).
    5. Catalog Persistence: Save indexed MediaRecord item into Amazon DynamoDB.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from apps.aws.providers import get_runtime
from apps.domain import CATEGORY_LABELS, SUBJECT_LABELS, MediaRecord, infer_category, infer_media_type, infer_subject, resolve_subject, usable_ocr_text
from pipeline.chunk_state import (
    KEY_ATTRIBUTE,
    MemoryChunkStore,
    get_utc_now_iso,
    init_file_pipeline_state,
    parent_key,
    save_chunks_batch,
)
from pipeline.chunking import chunk_transcribe_json
from pipeline.tier1_extract import extract_smart_summary

logger = logging.getLogger(__name__)

IMAGE_FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}
AUDIO_FORMATS = {".mp3": "mp3", ".wav": "wav", ".m4a": "mp4", ".flac": "flac"}
VIDEO_FORMATS = {".mp4": "mp4", ".mov": "mp4"}

LABEL_TRANSLATIONS = {
    # Technology / Study
    "computer": "Máy tính",
    "laptop": "Laptop",
    "electronics": "Thiết bị điện tử",
    "pc": "PC",
    "monitor": "Màn hình",
    "screen": "Màn hình hiển thị",
    "desk": "Bàn làm việc",
    "keyboard": "Bàn phím",
    "computer hardware": "Phần cứng",
    "hardware": "Thiết bị",
    "shelf": "Kệ sách",
    "bookcase": "Giá sách",
    "book": "Sách vở",
    "furniture": "Nội thất",
    "table": "Bàn",
    "study": "Học tập",
    # People
    "person": "Con người",
    "human": "Con người",
    "people": "Mọi người",
    "face": "Khuôn mặt",
    "head": "Khuôn mặt",
    "portrait": "Chân dung",
    "adult": "Người lớn",
    "male": "Nam giới",
    "female": "Nữ giới",
    "athlete": "Vận động viên",
    "player": "Cầu thủ",
    "soccer": "Bóng đá",
    "team": "Đội nhóm",
    "crowd": "Đám đông",
    # Animals / Pets
    "animal": "Động vật",
    "pet": "Thú cưng",
    "dog": "Chó",
    "cat": "Mèo",
    "mammal": "Động vật có vú",
    "tiger": "Hổ",
    "lion": "Sư tử",
    "bird": "Chim",
    "fish": "Cá",
    "wildlife": "Động vật hoang dã",
    # Nature / Scenes
    "nature": "Thiên nhiên",
    "landscape": "Cảnh quan",
    "plant": "Cây cối",
    "tree": "Cây xanh",
    "vegetation": "Thảm thực vật",
    "land": "Cảnh vật",
    "outdoors": "Ngoài trời",
    "beach": "Bãi biển",
    "mountain": "Núi non",
    "sunset": "Hoàng hôn",
    "sunrise": "Bình minh",
    "sky": "Bầu trời",
    "cloud": "Mây trời",
    "sea": "Biển cả",
    "water": "Mặt nước",
    "building": "Tòa nhà",
    "city": "Đô thị",
    "street": "Đường phố",
    "road": "Đường đi",
    "intersection": "Ngã tư",
    "flower": "Hoa tươi",
    "flower arrangement": "Bình hoa",
    "transportation": "Phương tiện",
    "vehicle": "Xe cộ",
    "car": "Ô tô",
    "boat": "Thuyền bè",
    # Food / Drink
    "food": "Món ăn",
    "meal": "Bữa ăn",
    "dish": "Đĩa ăn",
    "lunch": "Bữa ăn",
    "dinner": "Bữa ăn",
    "drink": "Đồ uống",
    "beverage": "Nước uống",
    "coffee": "Cà phê",
    "tea": "Trà",
    "restaurant": "Nhà hàng",
    "cafeteria": "Quán ăn",
    "indoors": "Trong phòng",
    # Receipts / Documents
    "receipt": "Hóa đơn",
    "invoice": "Biên lai",
    "whiteboard": "Bảng viết",
    "white board": "Bảng viết",
    "blackboard": "Bảng đen",
    "black board": "Bảng đen",
    "document": "Tài liệu",
    "paper": "Giấy tờ",
    "text": "Văn bản",
    # Audio / Video
    "speech": "Giọng nói",
    "audio": "Ghi âm",
    "video": "Video",
    "music": "Âm thanh",
}


def translate_labels(labels: list[str]) -> list[str]:
    """Translate raw Rekognition English labels to clean, natural Vietnamese tags."""
    seen = set()
    vietnamese_tags = []
    for l in labels:
        clean_key = l.lower().strip()
        trans = LABEL_TRANSLATIONS.get(clean_key, l.capitalize())
        # Filter out noisy tags
        if trans.lower() in {"accessories", "bag", "handbag", "clothing", "apparel"}:
            continue
        if trans not in seen:
            seen.add(trans)
            vietnamese_tags.append(trans)
    return vietnamese_tags[:6]


def _clean_ocr_snippet(ocr_text: str) -> str:
    """Extract a clean, readable text snippet from OCR, filtering out noisy symbols."""
    lines = [line.strip() for line in usable_ocr_text(ocr_text).splitlines() if line.strip()]
    if lines:
        combined = " • ".join(lines[:3])
        return combined[:80]
    return ""


def _in_lambda() -> bool:
    return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def _maybe_embed(record: MediaRecord) -> None:
    runtime = get_runtime()
    bedrock_client = getattr(runtime.planner, "client", None)
    if bedrock_client is None:
        return
    from apps.search.vector_engine import maybe_store_embedding

    blob = " ".join([
        record.filename or "",
        " ".join(record.labels or []),
        record.ocr_text or "",
        record.transcript or "",
        record.summary or "",
    ])
    record.embedding = maybe_store_embedding(blob, bedrock_client=bedrock_client)


def _write_thumb(file_id: str, object_key: str) -> Optional[str]:
    runtime = get_runtime()
    try:
        from apps.aws.image_convert import make_thumbnail_jpeg

        raw = runtime.store.get_bytes(object_key)
        jpeg = make_thumbnail_jpeg(raw)
        key = f"thumbs/{file_id}.jpg"
        runtime.store.put_bytes(key, jpeg, "image/jpeg")
        return key
    except Exception as exc:
        logger.warning("thumbnail skipped file_id=%s: %s", file_id, exc)
        return None


def _offload_transcript_if_large(record: MediaRecord, transcript: str, runtime: Any) -> str:
    """Offload transcripts exceeding 250KB to S3 to prevent DynamoDB 400KB limit overflow."""
    if not transcript:
        return ""
    if len(transcript.encode("utf-8")) > 250 * 1024:
        bucket = getattr(getattr(runtime, "store", None), "bucket", "") or os.environ.get("MEDIA_BUCKET", "agentsys-media-local")
        s3_key = f"transcripts/raw/{record.file_id}.json"
        raw_json = json.dumps({"file_id": record.file_id, "transcript": transcript}, ensure_ascii=False).encode("utf-8")
        if hasattr(runtime, "store") and hasattr(runtime.store, "put_bytes"):
            try:
                runtime.store.put_bytes(s3_key, raw_json, "application/json")
            except Exception as exc:
                logger.warning("Failed to offload raw transcript to S3 for %s: %s", record.file_id, exc, exc_info=True)
        record.transcript_s3_uri = f"s3://{bucket}/{s3_key}"
        record.has_extended_transcript = True
        return transcript[:15000] + " ... [Full transcript stored in S3]"
    return transcript


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
            labels, ocr = runtime.vision.analyze_image(object_key, name)
            record.analysis_source = "rekognition"
            record.thumb_key = _write_thumb(file_id, object_key)
        elif media_type in {"audio", "video"}:
            media_format = {**AUDIO_FORMATS, **VIDEO_FORMATS}.get(ext, "mp4")
            speech = runtime.speech
            if not hasattr(speech, "start_job"):
                raise RuntimeError("Amazon Transcribe is required")
            job_name = speech.start_job(object_key, media_format, file_id=file_id)
            if not job_name:
                raise RuntimeError("Amazon Transcribe did not start")
            record.transcribe_job_name = job_name
            if _in_lambda():
                record.labels = ["Giọng nói"]
                record.category = infer_category(media_type, record.labels, name)
                record.summary = "Đang chờ Amazon Transcribe hoàn tất (EventBridge)."
                record.status = "INDEXING"
                record.analysis_source = "transcribe-indexing"
                runtime.catalog.put(record)
                runtime.metrics.emit("MediaIngested", 1)
                return record
            transcript = speech.wait_for_job(job_name)
            record.analysis_source = "transcribe"
            labels = ["Giọng nói", "Ghi âm"] if transcript else ["Phương tiện"]
        else:
            labels = ["Tài liệu"]
            record.analysis_source = runtime.provider

        blob = " ".join([*labels, usable_ocr_text(ocr), transcript, name])
        bedrock_client = getattr(runtime.planner, "client", None)
        record.category = infer_category(media_type, labels, blob, bedrock_client=bedrock_client)
        record.labels = translate_labels(labels)
        record.ocr_text = usable_ocr_text(ocr)
        record.transcript = _offload_transcript_if_large(record, transcript, runtime)
        record.subject = infer_subject(record.labels, record.ocr_text, transcript, name, bedrock_client=bedrock_client)
        record.subject = resolve_subject(record)
        record.summary = _build_summary(record)
        record.status = "READY"
        record.error = None
        _maybe_embed(record)
        runtime.catalog.put(record)
        runtime.metrics.emit("MediaIngested", 1)
        return record
    except Exception as exc:
        logger.exception("ingest_failed file_id=%s", file_id)
        record.status = "FAILED"
        record.error = str(exc)
        runtime.catalog.put(record)
        runtime.metrics.emit("MediaIngestFailed", 1)
        raise


def _extract_audio_highlights(text: str) -> Optional[str]:
    if not text:
        return None
    points = []
    pres = re.search(r"(?:trình bày|thuyết trình)[^\.\,]*?(\d+\s*phút)", text, re.IGNORECASE)
    if pres:
        points.append(f"Thuyết trình ({pres.group(1).strip()}/nhóm)")

    exam = re.search(r"thi lý thuyết[^\.\,]*?(?:ngày\s*)?(\d+\s*tháng\s*\d+|\d+/\d+)", text, re.IGNORECASE)
    if exam:
        points.append(f"Thi lý thuyết: {exam.group(1).strip()}")

    subm = re.search(r"(\d+\s*tháng\s*\d+|\d+/\d+)[^\.\,]*?nộp", text, re.IGNORECASE) or re.search(
        r"nộp[^\.\,]*?(\d+\s*tháng\s*\d+|\d+/\d+)", text, re.IGNORECASE
    )
    if subm:
        points.append(f"Hạn nộp đồ án: {subm.group(1).strip()}")

    score = re.search(r"(\d+\s*tháng\s*\d+|\d+/\d+)[^\.\,]*?(?:có\s*)?điểm", text, re.IGNORECASE)
    if score:
        points.append(f"Công bố điểm: {score.group(1).strip()}")

    if re.search(r"(bảo vệ|chuẩn đầu ra|anh văn|tốt nghiệp|thủ dưỡng)", text, re.IGNORECASE):
        points.append("Lưu ý bảo vệ & chuẩn đầu ra")

    if len(points) >= 2:
        return "Hướng dẫn đồ án & lịch thi: " + " · ".join(points)
    return None


def _build_summary(record: MediaRecord) -> str:
    category_name = CATEGORY_LABELS.get(record.category, record.category)
    subject_name = SUBJECT_LABELS.get(resolve_subject(record), "")
    subject_bit = f" · môn {subject_name}" if subject_name else ""

    if record.media_type == "audio":
        highlights = _extract_audio_highlights(record.transcript)
        if highlights:
            return highlights
        if record.transcript and not record.transcript.startswith("Bản ghi"):
            clean_first = record.transcript.strip()[:100].rstrip(".")
            heading = subject_name or "bài giảng"
            return f"Bản ghi âm {heading}: \"{clean_first}...\""
        return f"File ghi âm đã lưu trữ{subject_bit} trong danh mục {category_name}."

    if record.media_type == "video":
        return f"Tệp video đa phương tiện{subject_bit} trong danh mục {category_name}."

    labels_str = ", ".join(record.labels[:4]) if record.labels else ""
    ocr_snippet = _clean_ocr_snippet(record.ocr_text)

    if record.category == "scenes":
        return f"Ảnh phong cảnh & du lịch ({labels_str.lower()})." + (f' Văn bản: "{ocr_snippet}".' if ocr_snippet else "")
    if record.category == "food":
        return f"Ảnh ẩm thực & món ăn ({labels_str.lower()})."
    if record.category == "people":
        return f"Ảnh con người & nhân vật ({labels_str.lower()})."
    if record.category == "pets":
        return f"Ảnh thú cưng & động vật ({labels_str.lower()})."
    if record.category == "receipts":
        return f'Hóa đơn / Biên lai thanh toán. Văn bản: "{ocr_snippet or labels_str}".'

    heading = f"Tài liệu {subject_name}" if subject_name else "Tài liệu học tập"
    if ocr_snippet:
        return f'{heading}: "{ocr_snippet}".'
    if labels_str:
        return f"Ảnh nhận diện {labels_str.lower()}{subject_bit}."

    return f"Tài liệu {record.filename} đã được phân loại vào {category_name}{subject_bit}."


def _extract_file_id_from_job_name(job_name: str) -> Optional[str]:
    """Extract file_id from new-format job name: agentsys--{file_id}--{key}."""
    if job_name.startswith("agentsys--") and "--" in job_name[len("agentsys--"):]:
        rest = job_name[len("agentsys--"):]
        parts = rest.split("--", 1)
        if len(parts) == 2 and parts[0]:
            return parts[0]
    return None


def find_record_for_transcribe_job(job_name: str) -> Optional[MediaRecord]:
    runtime = get_runtime()

    # Fast path: new-format job name encodes file_id → DynamoDB GetItem.
    file_id = _extract_file_id_from_job_name(job_name)
    if file_id:
        record = runtime.catalog.get(file_id)
        if record is not None:
            return record

    # Slow path (backward compat): old-format agentsys-uploads-xxx → scan.
    for rec in runtime.catalog.list_all():
        if rec.transcribe_job_name == job_name:
            return rec
    if job_name.startswith("agentsys-"):
        remainder = job_name[len("agentsys-") :]
        object_key = remainder.replace("-", "/", 1)
        for rec in runtime.catalog.list_all():
            if rec.s3_key == object_key or rec.file_id in job_name:
                return rec
    return None


def _refine_chunk_with_bedrock(
    chunk_text: str,
    bedrock_client: Any = None,
    model_id: str = "amazon.nova-lite-v1:0",
) -> str:
    """Summarize an individual transcript chunk using Bedrock Nova Lite."""
    if not chunk_text or not chunk_text.strip():
        return ""
    if bedrock_client is None:
        clean = chunk_text.strip().split("\n")[0].split(". ")[0].strip()
        return (clean[:190] + "...") if len(clean) > 190 else clean

    system_prompt = (
        "Bạn là trợ lý AI học thuật cho AgentSys. Hãy tóm tắt đoạn bài giảng sau thành 1-2 câu ngắn gọn, "
        "giữ lại các thuật ngữ chuyên ngành quan trọng và mốc thời gian nếu có. Trả về văn bản thuần không markdown."
    )
    try:
        response = bedrock_client.converse(
            modelId=model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": chunk_text}]}],
            inferenceConfig={"maxTokens": 150, "temperature": 0},
        )
        return response["output"]["message"]["content"][0]["text"].strip()
    except Exception as exc:
        logger.warning("Bedrock chunk refine failed: %s. Using truncated text.", exc)
        clean = chunk_text.strip().split("\n")[0].split(". ")[0].strip()
        return (clean[:190] + "...") if len(clean) > 190 else clean


def _mark_record_ready(runtime: Any, record: MediaRecord) -> None:
    """Flip the catalog record to READY without a full PutItem.

    ``DynamoCatalog.put`` is a PutItem (whole-item replace) and would erase the Tier-2
    bookkeeping (``total_chunks`` / ``chunks_completed`` / ``provisional_summary``) written by
    ``init_file_pipeline_state``. On DynamoDB we therefore patch just the status fields with an
    UpdateItem; non-DynamoDB catalogs (tests, standalone) fall back to ``put``.
    """
    record.status = "READY"
    record.error = None
    table = getattr(runtime.catalog, "table", None)
    if table is None or not hasattr(table, "update_item"):
        runtime.catalog.put(record)
        return
    table.update_item(
        Key=parent_key(record.file_id),
        UpdateExpression="SET #st = :ready, pipeline_status = :ps, updated_at = :now REMOVE #err",
        ConditionExpression=f"attribute_exists({KEY_ATTRIBUTE})",
        ExpressionAttributeNames={"#st": "status", "#err": "error"},
        ExpressionAttributeValues={
            ":ready": "READY",
            ":ps": record.pipeline_status,
            ":now": get_utc_now_iso(),
        },
    )


def apply_transcribe_job(job_name: str, job_status: str) -> dict:
    runtime = get_runtime()
    record = find_record_for_transcribe_job(job_name)
    if record is None:
        logger.warning("transcribe_job_no_record job=%s", job_name)
        return {"ok": True, "job_name": job_name, "status": job_status, "warning": "record not found", "source": "EventBridge"}

    if job_status == "FAILED":
        record.status = "FAILED"
        record.error = f"Amazon Transcribe job failed: {job_name}"
        runtime.catalog.put(record)
        runtime.metrics.emit("MediaIngestFailed", 1)
        return {"ok": True, "file_id": record.file_id, "status": "FAILED", "source": "EventBridge"}

    speech = runtime.speech
    transcript = ""
    transcribe_payload: dict = {}
    if hasattr(speech, "read_job_payload"):
        transcribe_payload = speech.read_job_payload(job_name)
        transcripts = transcribe_payload.get("results", {}).get("transcripts", [])
        if transcripts and transcripts[0].get("transcript"):
            transcript = transcripts[0].get("transcript", "").strip()
    if not transcript and hasattr(speech, "read_job_transcript"):
        transcript = speech.read_job_transcript(job_name)

    if not transcript:
        record.status = "FAILED"
        record.error = "Transcribe COMPLETED but transcript could not be read"
        runtime.catalog.put(record)
        return {"ok": False, "file_id": record.file_id, "error": record.error, "source": "EventBridge"}

    raw_transcript = transcript
    record.transcript = _offload_transcript_if_large(record, raw_transcript, runtime)
    record.labels = translate_labels(["Giọng nói", "Ghi âm"])
    bedrock_client = getattr(runtime.planner, "client", None)
    record.category = infer_category(
        record.media_type,
        record.labels,
        f"{raw_transcript} {record.filename}",
        bedrock_client=bedrock_client,
    )
    record.subject = infer_subject(
        record.labels,
        record.ocr_text,
        raw_transcript,
        record.filename,
        bedrock_client=bedrock_client,
    )
    record.subject = resolve_subject(record)

    # 1. Tier 1 Fast Extraction: Independent Announcements & Topic Overview (~10-50ms)
    tier1_meta = extract_smart_summary(raw_transcript)
    announcements = tier1_meta.get("announcements", [])
    topic_summary = tier1_meta.get("topic_summary", "")

    provisional_parts = []
    if announcements:
        provisional_parts.append("Lịch & Thông báo: " + " · ".join(announcements))
    if topic_summary:
        provisional_parts.append(topic_summary)
    provisional_summary = " · ".join(provisional_parts) if provisional_parts else _build_summary(record)

    record.summary = provisional_summary
    record.error = None
    record.analysis_source = "transcribe"
    _maybe_embed(record)

    # 2. Tier 2: Silence & Segment-Aware Chunking. The Tier-2 state (parent counters + PENDING
    #    chunk rows) is made durable BEFORE the record is announced READY, so a DynamoDB Streams
    #    consumer can never observe READY without pipeline state, and the counters cannot be
    #    wiped by a later full-item write.
    table = getattr(runtime.catalog, "table", None)
    store_or_table = table if table is not None else MemoryChunkStore()

    payload_for_chunking = transcribe_payload or {"results": {"transcripts": [{"transcript": raw_transcript}]}}
    chunks = chunk_transcribe_json(payload_for_chunking, record.file_id)

    # 2a. Persist the heavy Tier-1 fields while the record is still INDEXING. DynamoCatalog.put
    #     is a PutItem (whole-item replace), so it must land BEFORE init_file_pipeline_state
    #     writes total_chunks / chunks_completed onto the same item.
    record.status = "INDEXING"
    record.pipeline_status = "REFINING" if chunks else "PROVISIONAL_READY"
    runtime.catalog.put(record)

    # 2b. Durable Tier-2 state. A failure here is surfaced (FAILED + re-raise -> Lambda error,
    #     alarms, retry) instead of leaving a READY record whose refinement silently never runs.
    if chunks:
        try:
            init_file_pipeline_state(
                store_or_table, record.file_id, total_chunks=len(chunks), provisional_summary=tier1_meta
            )
            save_chunks_batch(store_or_table, record.file_id, chunks)
        except Exception as exc:
            logger.exception("tier2_init_failed file_id=%s", record.file_id)
            record.status = "FAILED"
            record.pipeline_status = "REFINE_INIT_FAILED"
            record.error = f"Tier-2 chunk pipeline init failed: {exc}"
            runtime.catalog.put(record)
            runtime.metrics.emit("MediaIngestFailed", 1)
            raise
        logger.info("tier2_chunking_saved_for_aggregator file_id=%s total_chunks=%d", record.file_id, len(chunks))

    # 3. Only now flip the record to READY (UpdateItem: keeps the counters written in 2b).
    _mark_record_ready(runtime, record)
    runtime.metrics.emit("MediaIngested", 1)
    logger.info("tier1_provisional_ready file_id=%s summary=%r", record.file_id, provisional_summary[:100])

    logger.info("dynamodb_transcript_updated file_id=%s", record.file_id)
    return {"ok": True, "file_id": record.file_id, "status": "READY", "source": "EventBridge"}
