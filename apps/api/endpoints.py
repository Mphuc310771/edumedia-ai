from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from apps.agent.search import execute_search
from apps.api.auth import verify_api_key
from apps.api.rate_limit import limiter
from apps.api.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    MediaItemOut,
    ProcessRequest,
    StatusResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from apps.aws.memory import MemoryObjectStore
from apps.aws.providers import get_runtime
from apps.domain import CATEGORY_LABELS, MediaRecord, ingest_pipeline
from apps.workers.ingestion import ingest_object

router = APIRouter()


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


def to_item_out(
    record: MediaRecord,
    score: float | None = None,
    matched_on: list[str] | None = None,
    matched_fields: list[str] | None = None,
) -> MediaItemOut:
    runtime = get_runtime()
    url = record.preview_url or ""
    if not url and record.s3_key:
        try:
            url = runtime.store.presign_get(record.s3_key)
        except Exception:
            url = ""
    return MediaItemOut(
        id=record.file_id,
        filename=record.filename,
        type=record.media_type,
        url=url,
        thumbnailUrl=record.preview_url,
        size=_human_size(record.size_bytes),
        date=record.created_at.replace("T", " ")[:16],
        category=record.category,
        categoryLabel=CATEGORY_LABELS.get(record.category, record.category),
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
        pipeline=ingest_pipeline(record.media_type),
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


@router.put("/local-upload/{object_key:path}")
async def local_upload(object_key: str, request: Request, content_type: str = "application/octet-stream"):
    runtime = get_runtime()
    if not isinstance(runtime.store, MemoryObjectStore):
        raise HTTPException(status_code=404, detail="Local upload is only available in memory mode")
    body = await request.body()
    runtime.store.put_bytes(object_key, body, content_type)
    return {"ok": True, "bytes": len(body)}


@router.get("/local-object/{object_key:path}")
def local_object(object_key: str):
    runtime = get_runtime()
    if not isinstance(runtime.store, MemoryObjectStore):
        raise HTTPException(status_code=404, detail="Not found")
    payload = runtime.store.get_object(object_key)
    if not payload:
        raise HTTPException(status_code=404, detail="Object not found")
    body, content_type = payload
    from fastapi.responses import Response

    return Response(content=body, media_type=content_type)


@router.post("/process", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_api_key)])
def trigger_media_processing(payload: ProcessRequest):
    object_key = payload.object_key or f"uploads/{payload.file_id}"
    try:
        record = ingest_object(
            file_id=payload.file_id,
            object_key=object_key,
            filename=payload.filename,
            content_type=payload.content_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {exc}",
        ) from exc
    return {
        "message": "Media indexing completed",
        "file_id": record.file_id,
        "status": record.status,
    }


@router.post("/upload", response_model=MediaItemOut, dependencies=[Depends(verify_api_key)])
async def upload_and_ingest(file: UploadFile = File(...)):
    runtime = get_runtime()
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "upload.bin")[1]
    object_key = f"uploads/{file_id}{ext}"
    body = await file.read()
    runtime.store.put_bytes(object_key, body, file.content_type or "application/octet-stream")
    record = ingest_object(
        file_id=file_id,
        object_key=object_key,
        filename=file.filename,
        content_type=file.content_type or "",
    )
    record.size_bytes = len(body)
    runtime.catalog.put(record)
    return to_item_out(record)


@router.post("/upload-batch", response_model=list[MediaItemOut], dependencies=[Depends(verify_api_key)])
async def upload_batch_and_ingest(files: list[UploadFile] = File(...)):
    runtime = get_runtime()
    results = []
    for file in files:
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename or "upload.bin")[1]
        object_key = f"uploads/{file_id}{ext}"
        body = await file.read()
        runtime.store.put_bytes(object_key, body, file.content_type or "application/octet-stream")
        record = ingest_object(
            file_id=file_id,
            object_key=object_key,
            filename=file.filename,
            content_type=file.content_type or "",
        )
        record.size_bytes = len(body)
        runtime.catalog.put(record)
        results.append(to_item_out(record))
    return results


@router.get("/status/{file_id}", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
def check_media_status(file_id: str):
    record = get_runtime().catalog.get(file_id)
    if record is None:
        return StatusResponse(file_id=file_id, status="UNKNOWN", error="not found")
    return StatusResponse(file_id=file_id, status=record.status, error=record.error)


@router.get("/items", response_model=list[MediaItemOut], dependencies=[Depends(verify_api_key)])
def list_items():
    records = get_runtime().catalog.list_all()
    records.sort(key=lambda item: item.created_at, reverse=True)
    return [to_item_out(item) for item in records]


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
    get_runtime().catalog.clear()
    return {"message": "All media items cleared successfully"}


@router.delete("/{file_id}", dependencies=[Depends(verify_api_key)])
def delete_item(file_id: str):
    success = get_runtime().catalog.delete(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File ID not found")
    return {"message": "Deleted successfully", "file_id": file_id}
