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
    for key in (record.s3_key, record.thumb_key):
        if not key:
            continue
        try:
            store.delete_object(key)
        except Exception as exc:
            logger.warning("s3 delete skipped key=%s: %s", key, exc)


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
    )


@router.post("/upload-url", response_model=UploadUrlResponse, dependencies=[Depends(verify_api_key)])
def generate_upload_url(payload: UploadUrlRequest):
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(payload.filename)[1]
    object_key = f"uploads/{file_id}{ext}"
    runtime = get_runtime()
    try:
        url = runtime.store.presign_put(object_key, payload.content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create upload URL: {exc}",
        ) from exc
    return UploadUrlResponse(file_id=file_id, presigned_url=url, object_key=object_key)


def _run_ingest_background(file_id: str, object_key: str, filename: str | None, content_type: str) -> None:
    """Chạy ingest ở nền: ingest_object tự ghi trạng thái READY/FAILED vào catalog."""
    try:
        ingest_object(
            file_id=file_id,
            object_key=object_key,
            filename=filename,
            content_type=content_type,
        )
    except Exception:
        # ingest_object đã đánh dấu record FAILED và log; nuốt exception để không làm ồn background task
        pass


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
    content_hash = hashlib.md5(f"{clean_name}_{len(body)}".encode("utf-8")).hexdigest()[:10]
    return f"{safe_slug}-{content_hash}"


# Giới hạn 6MB cho upload trực tiếp đồng bộ nhằm tránh lỗi 413 của API Gateway (tối đa 10MB)
# và chống timeout/CPU Freeze trên AWS Lambda. Khuyến nghị dùng /upload-url cho tệp lớn.
MAX_DIRECT_UPLOAD_BYTES = 6 * 1024 * 1024


@router.post("/upload", response_model=MediaItemOut, dependencies=[Depends(verify_api_key)])
async def upload_and_ingest(file: UploadFile = File(...)):
    runtime = get_runtime()
    body = await file.read()
    if len(body) > MAX_DIRECT_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Tệp vượt quá giới hạn 6MB cho upload trực tiếp. Vui lòng sử dụng /upload-url để tải lên S3 qua Presigned URL.",
        )
    logger.warning("direct_sync_upload_used filename=%s size=%d. Khuyến nghị dùng /upload-url cho môi trường production.", file.filename, len(body))
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


@router.post("/upload-batch", response_model=list[MediaItemOut], dependencies=[Depends(verify_api_key)])
async def upload_batch_and_ingest(files: list[UploadFile] = File(...)):
    runtime = get_runtime()
    results = []
    for file in files:
        body = await file.read()
        if len(body) > MAX_DIRECT_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Tệp {file.filename} vượt quá giới hạn 6MB. Vui lòng sử dụng /upload-url.",
            )
        logger.warning("direct_sync_upload_used filename=%s size=%d", file.filename, len(body))
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
    records.sort(key=lambda item: item.created_at, reverse=True)
    return records


@router.get("/items", response_model=list[MediaItemOut], dependencies=[Depends(verify_api_key)])
def list_items():
    return [to_item_out(item) for item in _list_records()]


@router.get("/items/{file_id}/url", dependencies=[Depends(verify_api_key)])
def item_content_url(file_id: str):
    record = get_runtime().catalog.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File ID not found")
    return {
        "id": file_id,
        "url": _presign(record.s3_key),
        "thumbnailUrl": _presign(record.thumb_key or ""),
    }


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
def clear_all_items():
    runtime = get_runtime()
    for record in runtime.catalog.list_all(limit=None):
        _purge_objects(record)
    runtime.catalog.clear()
    return {"message": "All media items cleared successfully"}


@router.delete("/{file_id}", dependencies=[Depends(verify_api_key)])
def delete_item(file_id: str):
    runtime = get_runtime()
    record = runtime.catalog.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File ID not found")
    _purge_objects(record)
    runtime.catalog.delete(file_id)
    return {"message": "Deleted successfully", "file_id": file_id}
