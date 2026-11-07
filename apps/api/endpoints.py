"""FastAPI route endpoints for media uploads, processing, queries, and catalog management."""
from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from botocore.exceptions import ClientError

from apps.agent.search import execute_search
from apps.api.auth import verify_api_key
from apps.api.rate_limit import limiter
from apps.aws import aws_services
from apps.aws.aws_services import SQSQueue
from apps.api.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    MediaItemOut,
    ProcessRequest,
    StatusResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from apps.aws.providers import get_runtime
from apps.domain import (
    CATEGORY_LABELS,
    SUBJECT_LABELS,
    MediaRecord,
    infer_media_type,
    ingest_pipeline,
    resolve_subject,
)
from apps.workers.ingestion import ingest_object

router = APIRouter()
logger = logging.getLogger(__name__)


def _human_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "—"
    units = ["B", "KB", "MB", "GB"]
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size_bytes} B"


def _presign(object_key: str) -> str:
    if not object_key:
        return ""
    try:
        return get_runtime().store.presign_get(object_key)
    except Exception:
        return ""


def _purge_objects(record: MediaRecord) -> None:
    store = get_runtime().store
    raw_key = f"transcripts/raw/{record.file_id}.json" if getattr(record, "has_extended_transcript", False) else None
    for key in (record.s3_key, record.thumb_key, raw_key):
        if not key:
            continue
        try:
            store.delete_object(key)
        except Exception as exc:
            logger.warning("s3 delete skipped key=%s: %s", key, exc)


MAX_PUBLIC_UPLOAD_BYTES = 25 * 1024 * 1024  # 25MB public demo guardrail


def is_demo_record(record: MediaRecord) -> bool:
    if getattr(record, "is_demo_protected", False):
        return True
    lower_fn = (record.filename or "").lower()
    lower_fid = (record.file_id or "").lower()
    return lower_fn.startswith(("sample_", "sample-", "demo_", "demo-")) or \
           lower_fid.startswith(("sample_", "sample-", "demo_", "demo-"))


def to_item_out(
    record: MediaRecord,
    score: float | None = None,
    matched_on: list[str] | None = None,
    matched_fields: list[str] | None = None,
    *,
    include_original: bool = False,
) -> MediaItemOut:
    thumb = _presign(record.thumb_key or "")
    original = _presign(record.s3_key) if include_original else thumb
    subject = record.subject or resolve_subject(record)
    category = record.category
    demo_protected = is_demo_record(record)
    return MediaItemOut(
        id=record.file_id,
        filename=record.filename,
        type=record.media_type,
        url=original or thumb,
        thumbnailUrl=thumb or None,
        size=_human_size(record.size_bytes),
        date=record.created_at.replace("T", " ")[:16],
        category=category,
        categoryLabel=CATEGORY_LABELS.get(category, category),
        labels=record.labels,
        ocrText=record.ocr_text,
        transcript=record.transcript,
        summary=record.summary,
        status=record.status,
        tags=record.labels[:6],
        source=record.source,
        score=score,
        matchedOn=matched_on or [],
        matchedFields=matched_fields or [],
        pipeline=ingest_pipeline(record.media_type, record.analysis_source),
        error=record.error,
        analysisSource=record.analysis_source,
        subject=subject,
        subjectLabel=SUBJECT_LABELS.get(subject, ""),
        transcript_s3_uri=record.transcript_s3_uri,
        has_extended_transcript=record.has_extended_transcript,
        transcriptS3Uri=record.transcript_s3_uri,
        hasExtendedTranscript=record.has_extended_transcript,
        is_demo_protected=demo_protected,
        isDemoProtected=demo_protected,
    )


@router.post("/upload-url", response_model=UploadUrlResponse, dependencies=[Depends(verify_api_key)])
def generate_upload_url(payload: UploadUrlRequest):
    media_type = infer_media_type(payload.filename, payload.content_type)
    if media_type == "other":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng tệp không được hỗ trợ. Vui lòng tải ảnh (JPEG, PNG, WebP), âm thanh (MP3, M4A, WAV, FLAC), hoặc video (MP4, MOV, WebM).",
        )
    if payload.size_bytes is not None and payload.size_bytes > MAX_PUBLIC_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dung lượng tệp ({payload.size_bytes // (1024*1024)}MB) vượt quá giới hạn demo cho phép (tối đa 25MB).",
        )
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(payload.filename)[1]
    object_key = f"uploads/{file_id}{ext}"
    runtime = get_runtime()
    try:
        # Standardized 15-minute TTL (900 seconds) matching AWS Well-Architected Security Specification
        url = runtime.store.presign_put(object_key, payload.content_type, expires=900)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create upload URL: {exc}",
        ) from exc
    return UploadUrlResponse(file_id=file_id, presigned_url=url, upload_url=url, object_key=object_key)


def _run_ingest_background(file_id: str, object_key: str, filename: str | None, content_type: str) -> None:
    """Chạy ingest ở nền: ingest_object tự ghi trạng thái READY/FAILED vào catalog."""
    try:
        ingest_object(
            file_id=file_id,
            object_key=object_key,
            filename=filename,
            content_type=content_type,
        )
    except Exception as exc:
        logger.warning("Non-blocking operation failed for file_id %s: %s", file_id, exc, exc_info=True)


@router.post("/process", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_api_key)])
def trigger_media_processing(payload: ProcessRequest):
    """Yêu cầu xử lý phương tiện thủ công (manual trigger / fallback).

    Lưu ý: Trong luồng tải lên chuẩn từ Web, S3 ObjectCreated notification đã tự động
    đẩy sự kiện vào SQS IngestQueue. Endpoint này chỉ dùng cho fallback hoặc kiểm thử độc lập.
    """
    object_key = payload.object_key or f"uploads/{payload.file_id}"
    name = payload.filename or os.path.basename(object_key)
    runtime = get_runtime()
    stub = MediaRecord(
        file_id=payload.file_id,
        filename=name,
        s3_key=object_key,
        media_type=infer_media_type(name, payload.content_type),
        content_type=payload.content_type or "application/octet-stream",
        status="INDEXING",
        source="pipeline",
    )
    runtime.catalog.put(stub)

    # Đẩy message trực tiếp vào SQS Ingest Queue (tránh lỗi CPU Freeze của FastAPI BackgroundTasks trên Lambda)
    message = {
        "action": "process",
        "file_id": payload.file_id,
        "object_key": object_key,
        "filename": name,
        "content_type": payload.content_type or "",
    }
    enqueued = False
    try:
        queue = aws_services.SQSQueue()
        enqueued = queue.send_message(message)
    except Exception as exc:
        logger.warning("SQS enqueue failed for file_id=%s: %s", payload.file_id, exc)

    # Chế độ chạy local standalone khi không có SQS
    if not enqueued and not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        logger.info("Running local direct ingest fallback for file_id=%s", payload.file_id)
        _run_ingest_background(payload.file_id, object_key, payload.filename, payload.content_type)

    return {
        "message": "Media indexing started",
        "file_id": payload.file_id,
        "status": "INDEXING",
        "error": None,
    }


@router.post("/reprocess/{file_id}", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_api_key)])
def reprocess_item(file_id: str):
    """Phân tích lại một tệp đã FAILED từ S3 object đã lưu qua SQS queue."""
    runtime = get_runtime()
    record = runtime.catalog.get(file_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File ID not found")
    if not record.s3_key:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Record has no S3 object to reprocess")
    record.status = "INDEXING"
    record.error = None
    runtime.catalog.put(record)

    # Đẩy message trực tiếp vào SQS Ingest Queue
    message = {
        "action": "reprocess",
        "file_id": record.file_id,
        "object_key": record.s3_key,
        "filename": record.filename,
        "content_type": record.content_type,
    }
    enqueued = False
    try:
        queue = aws_services.SQSQueue()
        enqueued = queue.send_message(message)
    except Exception as exc:
        logger.warning("SQS enqueue failed for reprocess file_id=%s: %s", record.file_id, exc)

    # Chế độ chạy local standalone khi không có SQS
    if not enqueued and not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        logger.info("Running local direct reprocess fallback for file_id=%s", record.file_id)
        _run_ingest_background(record.file_id, record.s3_key, record.filename, record.content_type)

    return {"file_id": record.file_id, "status": "INDEXING", "error": None}


def make_file_id(filename: str, body: bytes) -> str:
    clean_name = os.path.basename(filename or "media.bin").strip()
    safe_slug = re.sub(r"[^0-9a-zA-Z._-]", "_", clean_name)[:30]
    content_hash = hashlib.md5(f"{clean_name}_{len(body)}".encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    return f"{safe_slug}-{content_hash}"


# Giới hạn 6MB cho upload trực tiếp đồng bộ nhằm tránh lỗi 413 của API Gateway (tối đa 10MB)
# và chống timeout/CPU Freeze trên AWS Lambda. Khuyến nghị dùng /upload-url cho tệp lớn.
MAX_DIRECT_UPLOAD_BYTES = 6 * 1024 * 1024


@router.post(
    "/upload",
    response_model=MediaItemOut,
    dependencies=[Depends(verify_api_key)],
    deprecated=True,
    summary="[DEPRECATED] Tải lên trực tiếp qua API Gateway",
)
async def upload_and_ingest(file: UploadFile = File(...)):
    """[DEPRECATED - DEV/TEST ONLY] Tải lên và xử lý đồng bộ qua API Gateway.

    LƯU Ý: Trong môi trường AWS Production, bắt buộc sử dụng Direct S3 Upload qua route /upload-url
    để bypass giới hạn payload API Gateway và đảm bảo nguyên tắc Least-Privilege IAM cho Lambda API.
    """
    runtime = get_runtime()
    body = await file.read()
    if len(body) > MAX_DIRECT_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Tệp vượt quá giới hạn 6MB cho upload trực tiếp. Vui lòng sử dụng /upload-url để tải lên S3 qua Presigned URL.",
        )
    logger.warning("deprecated_direct_sync_upload_used filename=%s size=%d. Dùng /upload-url cho production.", file.filename, len(body))
    file_id = make_file_id(file.filename or "upload.bin", body)
    ext = os.path.splitext(file.filename or "upload.bin")[1]
    # Use 'direct/' prefix to avoid triggering S3→SQS→Lambda duplicate ingestion.
    # The SQS event source filter only listens for 'uploads/' prefix (presigned PUT).
    object_key = f"direct/{file_id}{ext}"
    runtime.store.put_bytes(object_key, body, file.content_type or "application/octet-stream")
    record = ingest_object(
        file_id=file_id,
        object_key=object_key,
        filename=file.filename,
        content_type=file.content_type or "",
    )
    record.size_bytes = len(body)
    runtime.catalog.put(record)
    return to_item_out(record, include_original=True)


@router.post(
    "/upload-batch",
    response_model=list[MediaItemOut],
    dependencies=[Depends(verify_api_key)],
    deprecated=True,
    summary="[DEPRECATED] Tải lên nhiều tệp qua API Gateway",
)
async def upload_batch_and_ingest(files: list[UploadFile] = File(...)):
    """[DEPRECATED - DEV/TEST ONLY] Tải lên nhiều tệp qua API Gateway.

    LƯU Ý: Trong môi trường AWS Production, hãy sử dụng hàng đợi upload phía frontend
    với Presigned URL (/upload-url) để tải song song trực tiếp lên S3.
    """
    runtime = get_runtime()
    results = []
    for file in files:
        body = await file.read()
        if len(body) > MAX_DIRECT_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Tệp {file.filename} vượt quá giới hạn 6MB. Vui lòng sử dụng /upload-url.",
            )
        logger.warning("deprecated_direct_sync_upload_used filename=%s size=%d", file.filename, len(body))
        file_id = make_file_id(file.filename or "upload.bin", body)
        ext = os.path.splitext(file.filename or "upload.bin")[1]
        object_key = f"direct/{file_id}{ext}"
        runtime.store.put_bytes(object_key, body, file.content_type or "application/octet-stream")
        record = ingest_object(
            file_id=file_id,
            object_key=object_key,
            filename=file.filename,
            content_type=file.content_type or "",
        )
        record.size_bytes = len(body)
        runtime.catalog.put(record)
        results.append(to_item_out(record, include_original=True))
    return results


@router.get("/status/{file_id}", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
def check_media_status(file_id: str):
    record = get_runtime().catalog.get(file_id)
    if record is None:
        return StatusResponse(file_id=file_id, status="UNKNOWN", error="not found")
    return StatusResponse(file_id=file_id, status=record.status, error=record.error)


def _list_records():
    try:
        records = get_runtime().catalog.list_all()
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if "ResourceNotFound" in code:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Catalog DynamoDB chưa có. Cần sam deploy stack agentsys rồi sửa MEDIA_BUCKET trong .env.",
            ) from exc
        raise
    records.sort(key=lambda item: item.created_at or "", reverse=True)
    return records


@router.get("/items", response_model=list[MediaItemOut], dependencies=[Depends(verify_api_key)])
def list_items():
    return [to_item_out(item) for item in _list_records()]


@router.get("/items/{file_id}/url", dependencies=[Depends(verify_api_key)])
def item_content_url(file_id: str):
    record = get_runtime().catalog.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File ID not found")
    raw_transcript_key = f"transcripts/raw/{file_id}.json" if getattr(record, "has_extended_transcript", False) else None
    return {
        "id": file_id,
        "url": _presign(record.s3_key),
        "thumbnailUrl": _presign(record.thumb_key or ""),
        "transcriptUrl": _presign(raw_transcript_key) if raw_transcript_key else None,
        "transcriptS3Uri": record.transcript_s3_uri,
        "hasExtendedTranscript": getattr(record, "has_extended_transcript", False),
    }


@router.get("/items/{file_id}/transcript-raw", dependencies=[Depends(verify_api_key)])
def item_raw_transcript(file_id: str):
    import json
    from fastapi.responses import Response

    runtime = get_runtime()
    record = runtime.catalog.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File ID not found")
    raw_key = f"transcripts/raw/{file_id}.json"
    raw_bytes = None
    try:
        raw_bytes = runtime.store.get_bytes(raw_key)
    except Exception as exc:
        logger.debug("Failed to retrieve raw transcript %s: %s", raw_key, exc)
    if raw_bytes:
        return Response(content=raw_bytes, media_type="application/json")
    payload = json.dumps({"file_id": file_id, "transcript": record.transcript or ""}, ensure_ascii=False)
    return Response(content=payload, media_type="application/json")


@router.post("/agent/query", response_model=AgentQueryResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
def process_agent_query(request: Request, payload: AgentQueryRequest):
    plan, hits = execute_search(payload.user_query)
    results = [
        to_item_out(hit.record, hit.score, hit.matched_on, hit.matched_fields)
        for hit in hits
    ]
    if payload.file_id:
        results = [item for item in results if item.id == payload.file_id] or results
    return AgentQueryResponse(
        user_query=payload.user_query,
        execution_status="COMPLETED",
        plan=plan.model_dump(),
        results=results,
    )


@router.delete("/clear", dependencies=[Depends(verify_api_key)])
def clear_all_items(request: Request):
    runtime = get_runtime()
    records = runtime.catalog.list_all(limit=None)
    force_admin = request.headers.get("x-admin-force") == "true"
    cleared_count = 0
    protected_count = 0

    for record in records:
        if is_demo_record(record) and not force_admin:
            protected_count += 1
            continue
        _purge_objects(record)
        runtime.catalog.delete(record.file_id)
        cleared_count += 1

    return {
        "message": f"All media items cleared successfully (cleared {cleared_count}, protected {protected_count})",
        "cleared_count": cleared_count,
        "protected_count": protected_count,
    }


@router.delete("/{file_id}", dependencies=[Depends(verify_api_key)])
def delete_item(file_id: str, request: Request):
    runtime = get_runtime()
    record = runtime.catalog.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File ID not found")

    force_admin = request.headers.get("x-admin-force") == "true"
    if is_demo_record(record) and not force_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tệp mẫu được bảo vệ cho người dùng trải nghiệm demo (is_demo_protected: true). Không thể xóa.",
        )

    _purge_objects(record)
    runtime.catalog.delete(file_id)
    return {"message": "Deleted successfully", "file_id": file_id}
