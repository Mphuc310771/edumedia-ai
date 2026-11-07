"""Chunk State Schema & Resilient DynamoDB Atomic Update Helpers.

Handles individual chunk lifecycle states (PENDING, PROCESSING, DONE, FAILED) and
ensures race-condition-free progress tracking via DynamoDB atomic ADD expressions.

Key layout (STATIC, mirrors ``infra/template.yaml`` -> MetadataTable.KeySchema = ``file_id`` HASH only):

    parent (MediaRecord)  Key = {"file_id": "<file_id>"}
    chunk i               Key = {"file_id": "<file_id>#CHUNK#000i"}  + attribute parent_file_id="<file_id>"

The layout is deliberately hard-coded instead of introspecting ``table.key_schema``: boto3
lazy-loads that attribute through ``DescribeTable`` (and re-loads it after *every* resource
action), which is an extra round-trip per call and an IAM action the Lambda roles did not hold.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Literal, Optional, Union

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError, ParamValidationError

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

KEY_ATTRIBUTE = "file_id"          # template.yaml MetadataTable.KeySchema (HASH)
CHUNK_KEY_MARKER = "#CHUNK#"


def chunk_item_id(file_id: str, chunk_index: int) -> str:
    """``file_id`` value stored for chunk items (single-key table layout)."""
    return f"{file_id}{CHUNK_KEY_MARKER}{chunk_index:04d}"


def is_chunk_item_id(value: Any) -> bool:
    return isinstance(value, str) and CHUNK_KEY_MARKER in value


def parent_key(file_id: str) -> Dict[str, Any]:
    """DynamoDB Key of the parent MediaRecord item. No table introspection (no DescribeTable)."""
    return {KEY_ATTRIBUTE: file_id}


def chunk_key(file_id: str, chunk_index: int) -> Dict[str, Any]:
    """DynamoDB Key of chunk ``chunk_index`` belonging to ``file_id``."""
    return {KEY_ATTRIBUTE: chunk_item_id(file_id, chunk_index)}


def _is_conditional_failure(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def _read_parent_counters(table: Any, file_id: str) -> Dict[str, Any]:
    response = table.get_item(Key=parent_key(file_id), ConsistentRead=True)
    return response.get("Item") or {}


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

    # DynamoDB Table Resource. Intentionally an upsert (no attribute_exists guard): the ingest
    # worker always calls it with the real parent id, and standalone demos rely on it to seed state.
    if hasattr(store_or_table, "update_item"):
        now = get_utc_now_iso()
        store_or_table.update_item(
            Key=parent_key(file_id),
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
            # Single-key layout: the chunk row gets its own partition key and points back to
            # the parent through ``parent_file_id`` (what the Aggregator uses to resolve it).
            item[KEY_ATTRIBUTE] = chunk_item_id(file_id, chunk.chunk_index)
            item["parent_file_id"] = file_id
            store_or_table.put_item(Item=item)


def mark_chunk_completed(
    store_or_table: Any,
    file_id: str,
    chunk_index: int,
    chunk_summary: str,
) -> Dict[str, Any]:
    """Mark a chunk as DONE and perform ATOMIC increment on chunks_completed.

    Both writes are guarded with ConditionExpressions so that:
      * a wrong key can never materialise a ghost item (UpdateItem is an upsert by default),
      * an at-least-once redelivery of the same chunk event cannot double-count the parent.
    The returned dict always carries ``skipped=True`` when nothing was incremented.
    """
    if isinstance(store_or_table, MemoryChunkStore):
        return store_or_table.mark_completed(file_id, chunk_index, chunk_summary)

    # DynamoDB Table Resource
    now = get_utc_now_iso()
    # 1. Chunk item: (PENDING|PROCESSING|FAILED) -> DONE, only if the row exists and is not DONE yet.
    try:
        store_or_table.update_item(
            Key=chunk_key(file_id, chunk_index),
            UpdateExpression="SET #st = :done, summary = :sum, updated_at = :now",
            ConditionExpression=f"attribute_exists({KEY_ATTRIBUTE}) AND #st <> :done",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":done": "DONE",
                ":sum": chunk_summary,
                ":now": now,
            },
        )
    except ClientError as exc:
        if not _is_conditional_failure(exc):
            raise
        parent = _read_parent_counters(store_or_table, file_id)
        logger.info(
            "chunk_completion_skipped file_id=%s idx=%d reason=missing_or_already_done", file_id, chunk_index
        )
        return {
            "chunk_index": chunk_index,
            "status": "DONE",
            "skipped": True,
            "chunks_completed": int(parent.get("chunks_completed", 0)),
            "total_chunks": int(parent.get("total_chunks", 0)),
        }

    # 2. Atomic counter increment on the parent item. Requires the Tier-2 state to have been
    #    initialised (total_chunks present): never create a stub, never finalise against a
    #    default total of 1.
    try:
        response = store_or_table.update_item(
            Key=parent_key(file_id),
            UpdateExpression="ADD chunks_completed :inc SET updated_at = :now",
            ConditionExpression=f"attribute_exists({KEY_ATTRIBUTE}) AND attribute_exists(total_chunks)",
            ExpressionAttributeValues={
                ":inc": 1,
                ":now": now,
            },
            ReturnValues="ALL_NEW",
        )
        attributes = response.get("Attributes", {})
        skipped = False
    except ClientError as exc:
        if not _is_conditional_failure(exc):
            raise
        logger.warning(
            "parent_counter_skipped file_id=%s idx=%d reason=parent_missing_or_tier2_not_initialised",
            file_id,
            chunk_index,
        )
        attributes = _read_parent_counters(store_or_table, file_id)
        skipped = True

    return {
        "chunk_index": chunk_index,
        "status": "DONE",
        "skipped": skipped,
        "chunks_completed": int(attributes.get("chunks_completed", 0)),
        "total_chunks": int(attributes.get("total_chunks", 0)),
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
    response = store_or_table.update_item(
        Key=chunk_key(file_id, chunk_index),
        UpdateExpression="ADD retry_count :inc SET #st = :failed, last_error = :err, updated_at = :now",
        # Guard: never materialise a ghost row for a chunk that does not exist.
        ConditionExpression=f"attribute_exists({KEY_ATTRIBUTE})",
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


MAX_CHUNKS_PER_FILE = 1000          # sanity bound for total_chunks read from the parent row
_BATCH_GET_PAGE = 100                # DynamoDB BatchGetItem hard limit (keys per request)
_BATCH_GET_MAX_ROUNDS = 8            # UnprocessedKeys retry rounds per page
_FALLBACK_SCAN_PAGE_LIMIT = 250      # items evaluated per Scan page in the legacy fallback
_FALLBACK_SCAN_MAX_PAGES = 40        # hard stop for the fallback (<= 10,000 evaluated items)

_SERIALIZER = TypeSerializer()
_DESERIALIZER = TypeDeserializer()


def _encode_keys(keys: List[Dict[str, Any]], native: bool) -> List[Dict[str, Any]]:
    if native:
        return list(keys)
    return [{name: _SERIALIZER.serialize(value) for name, value in key.items()} for key in keys]


def _batch_get_chunks(table: Any, file_id: str, total_chunks: int) -> List[Dict[str, Any]]:
    """Strongly-consistent keyed reads of every chunk row of ``file_id`` (no table Scan).

    Chunk keys are deterministic (``<id>#CHUNK#000i`` for i < total_chunks), so the whole set
    is fetched with ceil(N/100) BatchGetItem calls regardless of table size.

    ``table.meta.client`` of a ``boto3.resource("dynamodb").Table(...)`` carries boto3's
    high-level DynamoDB transform (native Python <-> AttributeValue), so keys/items are exchanged
    as plain Python. If a raw low-level client is ever injected instead, botocore rejects the
    native keys with ParamValidationError and we switch to explicit (de)serialisation.
    """
    client = table.meta.client
    table_name = table.name  # resource identifier: does NOT trigger DescribeTable (table_name would)
    keys = [chunk_key(file_id, index) for index in range(total_chunks)]
    native = True
    items: List[Dict[str, Any]] = []
    for start in range(0, len(keys), _BATCH_GET_PAGE):
        page = keys[start : start + _BATCH_GET_PAGE]
        request: Optional[Dict[str, Any]] = {
            table_name: {"Keys": _encode_keys(page, native), "ConsistentRead": True}
        }
        rounds = 0
        while request:
            try:
                response = client.batch_get_item(RequestItems=request)
            except ParamValidationError:
                if not native:
                    raise
                native = False
                request = {table_name: {"Keys": _encode_keys(page, native), "ConsistentRead": True}}
                continue
            for raw in response.get("Responses", {}).get(table_name, []):
                items.append(raw if native else {name: _DESERIALIZER.deserialize(value) for name, value in raw.items()})
            unprocessed = (response.get("UnprocessedKeys") or {}).get(table_name, {})
            if not unprocessed.get("Keys"):
                break
            rounds += 1
            if rounds >= _BATCH_GET_MAX_ROUNDS:
                logger.warning(
                    "batch_get_chunks_unprocessed_keys_dropped file_id=%s remaining=%d",
                    file_id,
                    len(unprocessed["Keys"]),
                )
                break
            time.sleep(min(0.05 * (2**rounds), 1.0))
            request = {table_name: unprocessed}
    return items


def _scan_chunks_bounded(table: Any, file_id: str) -> List[Dict[str, Any]]:
    """Legacy fallback when the parent carries no ``total_chunks``: paginated, page-bounded Scan.

    ``Limit`` caps the items evaluated per page and ``_FALLBACK_SCAN_MAX_PAGES`` caps the total
    work, so a large table can neither exhaust Lambda memory nor run past the function timeout.
    """
    from boto3.dynamodb.conditions import Attr

    scan_kwargs: Dict[str, Any] = {
        "FilterExpression": Attr("parent_file_id").eq(file_id)
        | Attr(KEY_ATTRIBUTE).begins_with(f"{file_id}{CHUNK_KEY_MARKER}"),
        "Limit": _FALLBACK_SCAN_PAGE_LIMIT,
        "ConsistentRead": True,
    }
    items: List[Dict[str, Any]] = []
    pages = 0
    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        pages += 1
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        if pages >= _FALLBACK_SCAN_MAX_PAGES:
            logger.warning(
                "chunk_scan_page_bound_reached file_id=%s pages=%d chunk_rows=%d", file_id, pages, len(items)
            )
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return items


def get_file_chunks(
    store_or_table: Any,
    file_id: str,
    total_chunks: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Retrieve all chunks for a file sorted strictly by chunk_index.

    DynamoDB path: read ``total_chunks`` from the parent (unless given) and fetch the chunk rows
    by key with BatchGetItem. Only when the parent carries no Tier-2 state (legacy rows) does it
    fall back to a bounded Scan.
    """
    if isinstance(store_or_table, MemoryChunkStore):
        return store_or_table.list_chunks(file_id)

    if total_chunks is None:
        parent = _read_parent_counters(store_or_table, file_id)
        total_chunks = int(parent.get("total_chunks", 0) or 0)

    if 0 < total_chunks <= MAX_CHUNKS_PER_FILE:
        items = _batch_get_chunks(store_or_table, file_id, total_chunks)
    else:
        if total_chunks > MAX_CHUNKS_PER_FILE:
            logger.warning(
                "total_chunks_exceeds_bound file_id=%s total=%d bound=%d -> bounded scan",
                file_id,
                total_chunks,
                MAX_CHUNKS_PER_FILE,
            )
        items = _scan_chunks_bounded(store_or_table, file_id)

    # Only genuine chunk rows carry chunk_index; this drops any legacy/ghost rows such as
    # "<id>#CHUNK#0000#CHUNK#0000" that a previous buggy release may have left behind.
    items = [item for item in items if "chunk_index" in item]
    items.sort(key=lambda x: int(x.get("chunk_index", 0)))
    return items

