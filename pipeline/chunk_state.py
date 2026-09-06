"""Chunk State Schema & Resilient DynamoDB Atomic Update Helpers.

Handles individual chunk lifecycle states (PENDING, PROCESSING, DONE, FAILED) and
ensures race-condition-free progress tracking via DynamoDB atomic ADD expressions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Literal, Optional, Union

from pipeline.chunking import TranscriptChunk

logger = logging.getLogger(__name__)

ChunkStatus = Literal["PENDING", "PROCESSING", "DONE", "FAILED"]
PipelineStatus = Literal["PROVISIONAL_READY", "REFINING", "REFINED_COMPLETED", "REFINED_FAILED"]


def get_utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChunkRecord:
    file_id: str
    chunk_id: str
    chunk_index: int
    start_time: float
    end_time: float
    text: str
    status: ChunkStatus = "PENDING"
    retry_count: int = 0
    last_error: Optional[str] = None
    summary: Optional[str] = None
    updated_at: str = field(default_factory=get_utc_now_iso)

    def to_item(self) -> Dict[str, Any]:
        """Format chunk record for DynamoDB single-table or chunk storage."""
        return {
            "PK": f"FILE#{self.file_id}",
            "SK": f"CHUNK#{self.chunk_index:04d}",
            "file_id": self.file_id,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "start_time": str(self.start_time),
            "end_time": str(self.end_time),
            "text": self.text,
            "status": self.status,
            "retry_count": self.retry_count,
            "last_error": self.last_error or "",
            "summary": self.summary or "",
            "updated_at": self.updated_at,
        }


# ==============================================================================
# DYNAMODB / STORE HELPER INTERFACE
# ==============================================================================

class MemoryChunkStore:
    """In-memory store mimicking DynamoDB atomic semantics for local testing and standalone runs."""

    def __init__(self):
        self.files: Dict[str, Dict[str, Any]] = {}
        self.chunks: Dict[str, Dict[int, Dict[str, Any]]] = {}

    def init_file(self, file_id: str, total_chunks: int, provisional_summary: Optional[Dict[str, Any]] = None):
        self.files[file_id] = {
            "file_id": file_id,
            "total_chunks": total_chunks,
            "chunks_completed": 0,
            "pipeline_status": "REFINING" if total_chunks > 0 else "PROVISIONAL_READY",
            "provisional_summary": provisional_summary or {},
            "refined_summary": "",
            "updated_at": get_utc_now_iso(),
        }
        self.chunks.setdefault(file_id, {})

    def save_chunk(self, chunk: ChunkRecord):
        self.chunks.setdefault(chunk.file_id, {})
        self.chunks[chunk.file_id][chunk.chunk_index] = chunk.to_item()

    def mark_completed(self, file_id: str, chunk_index: int, chunk_summary: str) -> Dict[str, Any]:
        if file_id not in self.chunks or chunk_index not in self.chunks[file_id]:
            raise KeyError(f"Chunk {chunk_index} not found for file {file_id}")

        chunk = self.chunks[file_id][chunk_index]
        chunk["status"] = "DONE"
        chunk["summary"] = chunk_summary
        chunk["updated_at"] = get_utc_now_iso()

        # Atomic increment on parent
        parent = self.files.get(file_id, {"chunks_completed": 0, "total_chunks": 1})
        parent["chunks_completed"] = parent.get("chunks_completed", 0) + 1
        parent["updated_at"] = get_utc_now_iso()

        return {
            "chunk": chunk,
            "chunks_completed": parent["chunks_completed"],
            "total_chunks": parent.get("total_chunks", 1),
        }

    def mark_failed(self, file_id: str, chunk_index: int, error_msg: str, max_retries: int = 3) -> Dict[str, Any]:
        if file_id not in self.chunks or chunk_index not in self.chunks[file_id]:
            raise KeyError(f"Chunk {chunk_index} not found for file {file_id}")

        chunk = self.chunks[file_id][chunk_index]
        chunk["retry_count"] = chunk.get("retry_count", 0) + 1
        chunk["last_error"] = error_msg
        chunk["status"] = "FAILED"
        chunk["updated_at"] = get_utc_now_iso()
        return chunk

    def list_chunks(self, file_id: str) -> List[Dict[str, Any]]:
        file_chunks = self.chunks.get(file_id, {})
        # Sort strictly by chunk_index
        return [file_chunks[idx] for idx in sorted(file_chunks.keys())]

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        return self.files.get(file_id)


# Global default store for standalone/in-memory mode
_DEFAULT_STORE = MemoryChunkStore()


def get_default_store() -> MemoryChunkStore:
    return _DEFAULT_STORE


# ==============================================================================
# DYNAMODB BOTO3 ATOMIC HELPERS
# ==============================================================================

def _get_dynamo_key(table: Any, file_id: str, sk: Optional[str] = None) -> Dict[str, Any]:
    """Resolve DynamoDB Key dict based on table key schema (supports both PK/SK and file_id)."""
    key_schema = getattr(table, "key_schema", []) or []
    key_names = [k.get("AttributeName") for k in key_schema if isinstance(k, dict)]
    if "PK" in key_names:
        key = {"PK": f"FILE#{file_id}"}
        if "SK" in key_names:
            key["SK"] = sk or "METADATA"
        return key
    if sk and (sk.startswith("CHUNK#") or sk == "CHUNK"):
        return {"file_id": f"{file_id}#{sk}"}
    return {"file_id": file_id}


def init_file_pipeline_state(
    store_or_table: Any,
    file_id: str,
    total_chunks: int,
    provisional_summary: Optional[Dict[str, Any]] = None,
) -> None:
    """Initialize file pipeline state with total chunks and 0 completed."""
    if isinstance(store_or_table, MemoryChunkStore):
        store_or_table.init_file(file_id, total_chunks, provisional_summary)
        return

    # DynamoDB Table Resource
    if hasattr(store_or_table, "update_item"):
        now = get_utc_now_iso()
        key = _get_dynamo_key(store_or_table, file_id, "METADATA")
        store_or_table.update_item(
            Key=key,
            UpdateExpression="SET total_chunks = :tot, chunks_completed = :zero, pipeline_status = :st, provisional_summary = :ps, updated_at = :now",
            ExpressionAttributeValues={
                ":tot": total_chunks,
                ":zero": 0,
                ":st": "REFINING" if total_chunks > 0 else "PROVISIONAL_READY",
                ":ps": provisional_summary or {},
                ":now": now,
            },
        )


def save_chunks_batch(
    store_or_table: Any,
    file_id: str,
    chunks: List[TranscriptChunk],
) -> None:
    """Save newly created chunks in PENDING state."""
    for chunk in chunks:
        record = ChunkRecord(
            file_id=file_id,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_index,
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            text=chunk.text,
            status="PENDING",
        )
        if isinstance(store_or_table, MemoryChunkStore):
            store_or_table.save_chunk(record)
        elif hasattr(store_or_table, "put_item"):
            item = record.to_item()
            key_schema = getattr(store_or_table, "key_schema", []) or []
            key_names = [k.get("AttributeName") for k in key_schema if isinstance(k, dict)]
            if "file_id" in key_names and "SK" not in key_names:
                item["file_id"] = f"{file_id}#CHUNK#{chunk.chunk_index:04d}"
                item["parent_file_id"] = file_id
            store_or_table.put_item(Item=item)


def mark_chunk_completed(
    store_or_table: Any,
    file_id: str,
    chunk_index: int,
    chunk_summary: str,
) -> Dict[str, Any]:
    """Mark a chunk as DONE and perform ATOMIC increment on chunks_completed."""
    if isinstance(store_or_table, MemoryChunkStore):
        return store_or_table.mark_completed(file_id, chunk_index, chunk_summary)

    # DynamoDB Table Resource
    now = get_utc_now_iso()
    # 1. Update chunk item
    chunk_key = _get_dynamo_key(store_or_table, file_id, f"CHUNK#{chunk_index:04d}")
    store_or_table.update_item(
        Key=chunk_key,
        UpdateExpression="SET #st = :done, summary = :sum, updated_at = :now",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":done": "DONE",
            ":sum": chunk_summary,
            ":now": now,
        },
    )

    # 2. Atomic counter increment on parent metadata item
    parent_key = _get_dynamo_key(store_or_table, file_id, "METADATA")
    response = store_or_table.update_item(
        Key=parent_key,
        UpdateExpression="ADD chunks_completed :inc SET updated_at = :now",
        ExpressionAttributeValues={
            ":inc": 1,
            ":now": now,
        },
        ReturnValues="ALL_NEW",
    )
    attributes = response.get("Attributes", {})
    return {
        "chunk_index": chunk_index,
        "status": "DONE",
        "chunks_completed": int(attributes.get("chunks_completed", 0)),
        "total_chunks": int(attributes.get("total_chunks", 1)),
    }


def mark_chunk_failed(
    store_or_table: Any,
    file_id: str,
    chunk_index: int,
    error_message: str = "",
    error_msg: Optional[str] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Record chunk failure and increment retry_count."""
    err = error_msg if error_msg is not None else error_message
    if isinstance(store_or_table, MemoryChunkStore):
        return store_or_table.mark_failed(file_id, chunk_index, err, max_retries)

    now = get_utc_now_iso()
    chunk_key = _get_dynamo_key(store_or_table, file_id, f"CHUNK#{chunk_index:04d}")
    response = store_or_table.update_item(
        Key=chunk_key,
        UpdateExpression="ADD retry_count :inc SET #st = :failed, last_error = :err, updated_at = :now",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":inc": 1,
            ":failed": "FAILED",
            ":err": err[:500],
            ":now": now,
        },
        ReturnValues="ALL_NEW",
    )
    return response.get("Attributes", {})


def get_file_chunks(store_or_table: Any, file_id: str) -> List[Dict[str, Any]]:
    """Retrieve all chunks for a file sorted strictly by chunk_index."""
    if isinstance(store_or_table, MemoryChunkStore):
        return store_or_table.list_chunks(file_id)

    key_schema = getattr(store_or_table, "key_schema", []) or []
    key_names = [k.get("AttributeName") for k in key_schema if isinstance(k, dict)]
    from boto3.dynamodb.conditions import Attr, Key

    if "PK" in key_names:
        response = store_or_table.query(
            KeyConditionExpression=Key("PK").eq(f"FILE#{file_id}") & Key("SK").begins_with("CHUNK#")
        )
        items = response.get("Items", [])
    else:
        response = store_or_table.scan(
            FilterExpression=Attr("parent_file_id").eq(file_id) | Attr("file_id").begins_with(f"{file_id}#CHUNK#")
        )
        items = response.get("Items", [])

    items.sort(key=lambda x: int(x.get("chunk_index", 0)))
    return items

