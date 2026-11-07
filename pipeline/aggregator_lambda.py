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
    KEY_ATTRIBUTE,
    MemoryChunkStore,
    get_default_store,
    get_file_chunks,
    get_utc_now_iso,
    is_chunk_item_id,
    mark_chunk_completed,
    parent_key,
)

logger = logging.getLogger(__name__)


def _is_dynamodb_table(store: Any) -> bool:
    return not isinstance(store, MemoryChunkStore) and hasattr(store, "update_item")


def _resolve_store(explicit: Any = None) -> Any:
    """Return the chunk store to operate on.

    Order: explicit argument -> the live DynamoDB table behind the runtime catalog -> the
    in-memory store (unit tests / standalone runs). Falling straight back to the in-memory
    store inside the Lambda would make the handler operate on an empty store and never touch
    the real table.
    """
    if explicit is not None:
        return explicit
    try:
        from apps.aws.providers import get_runtime

        table = getattr(get_runtime().catalog, "table", None)
        if table is not None:
            return table
    except Exception as exc:  # pragma: no cover - defensive; runtime may be unavailable in tests
        logger.debug("runtime_table_unavailable_using_memory_store: %s", exc)
    return get_default_store()


def _get_bedrock_client() -> Any:
    try:
        from apps.aws.providers import get_runtime
        runtime = get_runtime()
        return getattr(runtime.planner, "client", None)
    except Exception:
        return None


def _refine_chunk_with_bedrock(
    chunk_text: str,
    bedrock_client: Any = None,
    model_id: str = "amazon.nova-lite-v1:0",
) -> str:
    """Summarize an individual transcript chunk using Bedrock Nova Lite."""
    if not chunk_text or not chunk_text.strip():
        return ""
    client = bedrock_client if bedrock_client is not None else _get_bedrock_client()
    if client is None:
        clean = chunk_text.strip().split("\n")[0].split(". ")[0].strip()
        return (clean[:190] + "...") if len(clean) > 190 else clean

    system_prompt = (
        "Bạn là trợ lý AI học thuật cho AgentSys. Hãy tóm tắt đoạn bài giảng sau thành 1-2 câu ngắn gọn, "
        "giữ lại các thuật ngữ chuyên ngành quan trọng và mốc thời gian nếu có. Trả về văn bản thuần không markdown."
    )
    try:
        response = client.converse(
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
    """Resolve the PARENT file_id of a DynamoDB Stream image.

    Resolution order:
      1. ``parent_file_id``  - written on every chunk row by ``save_chunks_batch``.
      2. ``PK`` = ``FILE#<id>`` - legacy single-table attribute kept on chunk rows.
      3. ``file_id``          - only when it is a genuine parent id (no ``#CHUNK#`` marker).

    A chunk-shaped ``file_id`` (``<id>#CHUNK#0000``) without a resolvable parent is skipped with
    a warning: using it as the parent id is exactly what produced ``<id>#CHUNK#0000#CHUNK#0000``
    ghost rows and left parents stuck in REFINING.
    """
    parent = record_dict.get("parent_file_id")
    if parent:
        return str(parent)

    pk = record_dict.get("PK")
    if isinstance(pk, str) and pk.startswith("FILE#"):
        candidate = pk.split("FILE#", 1)[1]
        if candidate and not is_chunk_item_id(candidate):
            return candidate

    file_id = record_dict.get("file_id")
    if not file_id:
        return None
    file_id = str(file_id)
    if is_chunk_item_id(file_id):
        logger.warning("orphan_chunk_row_skipped file_id=%s reason=no_parent_reference", file_id)
        return None
    return file_id


def reduce_and_finalize(
    file_id: str,
    store_or_table: Any = None,
    bedrock_client: Any = None,
) -> Dict[str, Any]:
    """Stitch chunk summaries in strict chunk_index order and finalize parent state idempotently.

    Uses ConditionExpression (pipeline_status <> 'REFINED_COMPLETED') to prevent race conditions
    when duplicate stream events or concurrent workers trigger the reduce phase.

    Args:
        file_id: Unique file identifier.
        store_or_table: DynamoDB table resource or MemoryChunkStore instance.
        bedrock_client: Optional Bedrock Runtime client.

    Returns:
        Dictionary with final stitched summary, status, and already_finalized flag.
    """
    store = _resolve_store(store_or_table)

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

    # 3. Collect and stitch chunk summaries (enrich with Bedrock if not yet refined)
    chunk_summaries = []
    client = bedrock_client if bedrock_client is not None else _get_bedrock_client()
    for c in sorted_chunks:
        summary_text = (c.get("summary") or "").strip()
        if not summary_text:
            text = (c.get("text") or "").strip()
            if text:
                summary_text = _refine_chunk_with_bedrock(text, bedrock_client=client)
                c["summary"] = summary_text
        if summary_text:
            chunk_summaries.append(summary_text)

    if chunk_summaries:
        final_summary = " · ".join(chunk_summaries)
    else:
        full_text = " ".join((c.get("text") or "").strip() for c in sorted_chunks)
        final_summary = full_text[:300].strip()

    now = get_utc_now_iso()

    # 4. Atomic conditional update on DynamoDB table. The parent key IS the MediaRecord item
    #    (single-key layout), so this single UpdateItem publishes the refined summary to the
    #    catalog as well. attribute_exists() guarantees a wrong id can never create a ghost row.
    if _is_dynamodb_table(store):
        try:
            store.update_item(
                Key=parent_key(file_id),
                UpdateExpression="SET summary = :sum, pipeline_status = :st, updated_at = :now",
                ConditionExpression=(
                    f"attribute_exists({KEY_ATTRIBUTE}) AND "
                    "(attribute_not_exists(pipeline_status) OR pipeline_status <> :st)"
                ),
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

    # 5. Finalize in-memory store and mirror the summary into the catalog record (standalone /
    #    test mode only). For a real DynamoDB table step 4 already updated the catalog item; a
    #    PutItem here would replace the whole item, wiping total_chunks/chunks_completed and
    #    emitting a redundant stream event.
    if isinstance(store, MemoryChunkStore):
        file_meta = store.files.get(file_id, {})
        file_meta["refined_summary"] = final_summary
        file_meta["pipeline_status"] = "REFINED_COMPLETED"
        file_meta["updated_at"] = now
        try:
            from apps.aws.providers import get_runtime

            runtime = get_runtime()
            if hasattr(runtime, "catalog") and hasattr(runtime.catalog, "get"):
                rec = runtime.catalog.get(file_id)
                if rec:
                    rec.summary = final_summary
                    rec.pipeline_status = "REFINED_COMPLETED"
                    runtime.catalog.put(rec)
        except Exception as exc:
            logger.debug("catalog_update_skipped file_id=%s: %s", file_id, exc)

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

    store = _resolve_store(store_or_table)
    sk = str(new_image.get("SK", "") or "")
    total_chunks = int(new_image.get("total_chunks", 0) or 0)
    chunks_completed = int(new_image.get("chunks_completed", 0) or 0)

    # Check if parent metadata record indicates all chunks are complete
    if (sk == "METADATA" or "total_chunks" in new_image) and total_chunks > 0:
        if chunks_completed >= total_chunks:
            pipeline_status = new_image.get("pipeline_status")
            if pipeline_status != "REFINED_COMPLETED":
                logger.info("all_chunks_completed file_id=%s (%d/%d)", file_id, chunks_completed, total_chunks)
                return reduce_and_finalize(file_id, store_or_table=store)

    # Check if this record is an individual chunk that transitioned to DONE or PENDING
    if sk.startswith("CHUNK#") or "chunk_index" in new_image:
        chunk_status = new_image.get("status")
        chunk_index = int(new_image.get("chunk_index", 0) or 0)
        chunk_text = new_image.get("text", "")

        if chunk_status == "PENDING":
            summary = _refine_chunk_with_bedrock(chunk_text)
            # Conditional-check outcomes (duplicate delivery / uninitialised parent) are absorbed
            # inside mark_chunk_completed; anything else (throttling, IAM) propagates so the ESM
            # retry + OnFailure destination can engage instead of being silently swallowed.
            res = mark_chunk_completed(store, file_id, chunk_index, chunk_summary=summary)
            total = int(res.get("total_chunks", 0) or 0)
            done = int(res.get("chunks_completed", 0) or 0)
            if total > 0 and done >= total:
                return reduce_and_finalize(file_id, store_or_table=store)

        elif chunk_status == "DONE":
            if isinstance(store, MemoryChunkStore):
                file_meta = store.get_file(file_id)
                if file_meta:
                    if file_meta.get("chunks_completed", 0) >= file_meta.get("total_chunks", 1):
                        return reduce_and_finalize(file_id, store_or_table=store)
            else:
                chunks = get_file_chunks(store, file_id)
                if chunks and all(c.get("status") == "DONE" for c in chunks):
                    return reduce_and_finalize(file_id, store_or_table=store)

    return None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entrypoint for DynamoDB Stream events.

    Properly separates parse errors from reduce execution failures.
    Reports batch item failures so AWS Lambda retry and DLQ can engage if reduce fails.
    """
    records = event.get("Records", [])
    logger.info("aggregator_lambda_invoked records_count=%d", len(records))

    # Resolve the real chunk store (DynamoDB table behind the catalog) once per invocation so
    # every record in the batch operates on the same backend.
    store = _resolve_store()
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
            result = process_stream_record(rec, store_or_table=store)
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
