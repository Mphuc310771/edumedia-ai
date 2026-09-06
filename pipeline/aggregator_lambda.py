"""Event-Driven Aggregator / Reduce Lambda Handler with Race Condition Protection.

Triggered via DynamoDB Streams when chunk items reach DONE or chunks_completed increments.
Enforces idempotent reduce pass via DynamoDB ConditionExpression (pipeline_status <> 'REFINED_COMPLETED'),
preventing duplicated executions on at-least-once stream deliveries.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from pipeline.chunk_state import (
    _get_dynamo_key,
    get_default_store,
    get_file_chunks,
    get_utc_now_iso,
    MemoryChunkStore,
)

logger = logging.getLogger(__name__)


def unwrap_dynamodb_image(image: Dict[str, Any]) -> Dict[str, Any]:
    """Convert DynamoDB attribute value map (e.g. {'S': 'val'}, {'N': '1'}) into standard Python dict."""
    result: Dict[str, Any] = {}
    for key, value_dict in (image or {}).items():
        if not isinstance(value_dict, dict):
            result[key] = value_dict
            continue
        for type_tag, val in value_dict.items():
            if type_tag == "S":
                result[key] = val
            elif type_tag == "N":
                result[key] = int(val) if "." not in val else float(val)
            elif type_tag == "BOOL":
                result[key] = bool(val)
            elif type_tag == "NULL":
                result[key] = None
            elif type_tag == "L":
                result[key] = [unwrap_dynamodb_image({"v": item})["v"] for item in val]
            elif type_tag == "M":
                result[key] = unwrap_dynamodb_image(val)
            else:
                result[key] = val
    return result


def extract_file_id(record_dict: Dict[str, Any]) -> Optional[str]:
    """Extract file_id from DynamoDB Stream record (supports single-table PK or direct file_id)."""
    if "file_id" in record_dict and record_dict["file_id"]:
        return str(record_dict["file_id"])
    pk = record_dict.get("PK", "")
    if pk.startswith("FILE#"):
        return pk.split("FILE#", 1)[1]
    return None


def reduce_and_finalize(
    file_id: str,
    store_or_table: Any = None,
) -> Dict[str, Any]:
    """Stitch chunk summaries in strict chunk_index order and finalize parent state idempotently.

    Uses ConditionExpression (pipeline_status <> 'REFINED_COMPLETED') to prevent race conditions
    when duplicate stream events or concurrent workers trigger the reduce phase.

    Args:
        file_id: Unique file identifier.
        store_or_table: DynamoDB table resource or MemoryChunkStore instance.

    Returns:
        Dictionary with final stitched summary, status, and already_finalized flag.
    """
    store = store_or_table or get_default_store()

    # 1. In-memory store idempotent check (for tests and local standalone runs)
    if isinstance(store, MemoryChunkStore):
        file_meta = store.files.get(file_id, {})
        if file_meta.get("pipeline_status") == "REFINED_COMPLETED":
            logger.info("reduce_already_finalized file_id=%s (in-memory check)", file_id)
            return {
                "file_id": file_id,
                "pipeline_status": "REFINED_COMPLETED",
                "already_finalized": True,
                "final_summary": file_meta.get("refined_summary", ""),
                "updated_at": file_meta.get("updated_at", ""),
            }

    chunks = get_file_chunks(store, file_id)
    if not chunks:
        logger.warning("reduce_and_finalize_no_chunks file_id=%s", file_id)
        return {
            "file_id": file_id,
            "pipeline_status": "REFINED_FAILED",
            "error": "no chunks found",
            "already_finalized": False,
        }

    # 2. Sort strictly by chunk_index to guarantee chronological flow
    sorted_chunks = sorted(chunks, key=lambda x: int(x.get("chunk_index", 0)))

    # 3. Collect and stitch chunk summaries
    chunk_summaries = []
    for c in sorted_chunks:
        summary_text = (c.get("summary") or "").strip()
        if summary_text:
            chunk_summaries.append(summary_text)

    if chunk_summaries:
        final_summary = " · ".join(chunk_summaries)
    else:
        full_text = " ".join((c.get("text") or "").strip() for c in sorted_chunks)
        final_summary = full_text[:300].strip()

    now = get_utc_now_iso()

    # 4. Atomic conditional update on DynamoDB table
    if hasattr(store, "update_item") and not isinstance(store, MemoryChunkStore):
        try:
            parent_key = _get_dynamo_key(store, file_id, "METADATA")
            store.update_item(
                Key=parent_key,
                UpdateExpression="SET summary = :sum, pipeline_status = :st, updated_at = :now",
                ConditionExpression="attribute_not_exists(pipeline_status) OR pipeline_status <> :st",
                ExpressionAttributeValues={
                    ":sum": final_summary,
                    ":st": "REFINED_COMPLETED",
                    ":now": now,
                },
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "ConditionalCheckFailedException":
                logger.info("reduce_already_finalized file_id=%s (ConditionalCheckFailedException caught)", file_id)
                return {
                    "file_id": file_id,
                    "pipeline_status": "REFINED_COMPLETED",
                    "already_finalized": True,
                }
            logger.error("reduce_finalize_dynamodb_error file_id=%s: %s", file_id, exc)
            raise

    # 5. Finalize in-memory store
    if isinstance(store, MemoryChunkStore):
        file_meta = store.files.get(file_id, {})
        file_meta["refined_summary"] = final_summary
        file_meta["pipeline_status"] = "REFINED_COMPLETED"
        file_meta["updated_at"] = now

    logger.info("reduce_and_finalize_success file_id=%s chunks=%d", file_id, len(sorted_chunks))
    return {
        "file_id": file_id,
        "pipeline_status": "REFINED_COMPLETED",
        "already_finalized": False,
        "chunks_count": len(sorted_chunks),
        "final_summary": final_summary,
        "updated_at": now,
    }


def process_stream_record(
    record: Dict[str, Any],
    store_or_table: Any = None,
) -> Optional[Dict[str, Any]]:
    """Process a single DynamoDB Stream record.

    Triggers reduce pass when all chunks have finished processing.
    """
    event_name = record.get("eventName", "")
    if event_name not in {"INSERT", "MODIFY"}:
        return None

    dynamodb_data = record.get("dynamodb", {})
    new_image_raw = dynamodb_data.get("NewImage", {})
    if not new_image_raw:
        return None

    new_image = unwrap_dynamodb_image(new_image_raw)
    file_id = extract_file_id(new_image)
    if not file_id:
        return None

    sk = new_image.get("SK", "")
    total_chunks = int(new_image.get("total_chunks", 0))
    chunks_completed = int(new_image.get("chunks_completed", 0))

    # Check if parent metadata record indicates all chunks are complete
    if (sk == "METADATA" or "total_chunks" in new_image) and total_chunks > 0:
        if chunks_completed >= total_chunks:
            pipeline_status = new_image.get("pipeline_status")
            if pipeline_status != "REFINED_COMPLETED":
                logger.info("all_chunks_completed file_id=%s (%d/%d)", file_id, chunks_completed, total_chunks)
                return reduce_and_finalize(file_id, store_or_table=store_or_table)

    # Check if this record is an individual chunk that transitioned to DONE
    if sk.startswith("CHUNK#") or "chunk_index" in new_image:
        chunk_status = new_image.get("status")
        if chunk_status == "DONE":
            store = store_or_table or get_default_store()
            if isinstance(store, MemoryChunkStore):
                file_meta = store.get_file(file_id)
                if file_meta:
                    if file_meta.get("chunks_completed", 0) >= file_meta.get("total_chunks", 1):
                        return reduce_and_finalize(file_id, store_or_table=store_or_table)

    return None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entrypoint for DynamoDB Stream events.

    Properly separates parse errors from reduce execution failures.
    Reports batch item failures so AWS Lambda retry and DLQ can engage if reduce fails.
    """
    records = event.get("Records", [])
    logger.info("aggregator_lambda_invoked records_count=%d", len(records))

    processed_files = []
    batch_item_failures = []

    for rec in records:
        dynamodb_info = rec.get("dynamodb", {})
        # AWS requirement for DynamoDB Streams ReportBatchItemFailures:
        # itemIdentifier MUST be the record's SequenceNumber (not eventID or custom string)
        seq_num = dynamodb_info.get("SequenceNumber")
        if not seq_num:
            item_id = rec.get("eventID") or rec.get("messageId") or ""
            logger.warning(
                "missing_sequence_number_fallback: record is missing dynamodb.SequenceNumber. Fallback item_id=%s record=%s",
                item_id,
                rec,
            )
        else:
            item_id = seq_num

        try:
            result = process_stream_record(rec)
            if result:
                if result.get("pipeline_status") == "REFINED_FAILED" or result.get("error"):
                    logger.warning("reduce_result_failed item_id=%s result=%s", item_id, result)
                    if item_id:
                        batch_item_failures.append({"itemIdentifier": str(item_id)})
                    try:
                        from apps.aws.providers import get_runtime
                        get_runtime().metrics.emit("MediaIngestFailed", 1)
                    except Exception:
                        pass
                else:
                    processed_files.append(result)
        except Exception as exc:
            logger.error("reduce_execution_failed item_id=%s record=%s: %s", item_id, rec, exc, exc_info=True)
            if item_id:
                batch_item_failures.append({"itemIdentifier": str(item_id)})
            else:
                raise
            try:
                from apps.aws.providers import get_runtime
                get_runtime().metrics.emit("MediaIngestFailed", 1)
            except Exception:
                pass

    response = {
        "ok": len(batch_item_failures) == 0,
        "processed_count": len(processed_files),
        "results": processed_files,
    }
    if batch_item_failures:
        response["batchItemFailures"] = batch_item_failures

    return response
