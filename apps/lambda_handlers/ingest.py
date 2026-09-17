import json
import logging
from typing import Any, List, Tuple
from urllib.parse import unquote_plus

from apps.aws.providers import get_runtime, reset_runtime
from apps.workers.ingestion import apply_transcribe_job, ingest_object

logger = logging.getLogger(__name__)

S3Object = Tuple[str, str]


def _from_s3_record(record: dict) -> List[S3Object]:
    bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])
    return [(bucket, key)]


def iter_s3_objects(event: dict) -> List[S3Object]:
    """Unwrap S3 ObjectCreated events, including the SQS envelope used in production."""
    found: List[S3Object] = []
    for record in event.get("Records") or []:
        if "s3" in record:
            found.extend(_from_s3_record(record))
            continue
        body = record.get("body")
        if not body:
            continue
        payload: Any = json.loads(body) if isinstance(body, str) else body
        if str(payload.get("Event", "")).startswith("s3:TestEvent"):
            continue
        for inner in payload.get("Records") or []:
            if "s3" in inner:
                found.extend(_from_s3_record(inner))
    return found


def handle_eventbridge_transcribe(event: dict) -> dict:
    """Write the real transcript into DynamoDB when Amazon Transcribe finishes."""
    detail = event.get("detail", {})
    job_name = detail.get("TranscriptionJobName", "")
    job_status = detail.get("TranscriptionJobStatus", "")
    logger.info("eventbridge_transcribe_event job=%s status=%s", job_name, job_status)
    result = apply_transcribe_job(job_name, job_status)
    result.setdefault("ok", True)
    result.setdefault("source", "EventBridge")
    return result


def handler(event, context):
    reset_runtime()

    # 1. Handle Amazon EventBridge Events (Transcribe Job State Change)
    if event.get("source") == "aws.transcribe":
        return handle_eventbridge_transcribe(event)

    # 2. Handle SQS-wrapped S3 ObjectCreated Events
    failures = []
    processed = []
    for record in event.get("Records") or []:
        message_id = record.get("messageId") or ""
        try:
            # 2a. Check for direct SQS action message (from /process or /reprocess)
            body = record.get("body")
            parsed_body = None
            if body:
                try:
                    parsed_body = json.loads(body) if isinstance(body, str) else body
                except Exception:
                    parsed_body = None

            if isinstance(parsed_body, dict) and parsed_body.get("action") in {"process", "reprocess"}:
                file_id = parsed_body.get("file_id")
                key = parsed_body.get("object_key")
                filename = parsed_body.get("filename") or (key.rsplit("/", 1)[-1] if key else "")
                content_type = parsed_body.get("content_type", "")
                if file_id and key:
                    action = parsed_body.get("action")
                    if action != "reprocess":
                        try:
                            existing = get_runtime().catalog.get(file_id)
                            if existing and getattr(existing, "status", "") == "READY":
                                logger.info("skip_duplicate_direct_action file_id=%s already READY", file_id)
                                processed.append({"file_id": getattr(existing, "file_id", file_id), "status": existing.status})
                                continue
                        except Exception:
                            pass
                    logger.info("sqs_direct_action action=%s file_id=%s key=%s", action, file_id, key)
                    item = ingest_object(file_id=file_id, object_key=key, filename=filename, content_type=content_type)
                    processed.append({"file_id": item.file_id, "status": item.status})
                    continue

            # 2b. Handle SQS-wrapped S3 ObjectCreated events
            objects = iter_s3_objects({"Records": [record]})
            for bucket, key in objects:
                if not key.startswith("uploads/"):
                    logger.info("skip_non_upload bucket=%s key=%s", bucket, key)
                    continue
                filename = key.rsplit("/", 1)[-1]
                file_id = filename.rsplit(".", 1)[0]
                try:
                    existing = get_runtime().catalog.get(file_id)
                    if existing and getattr(existing, "status", "") == "READY":
                        logger.info("skip_duplicate_s3_ingest file_id=%s already READY", file_id)
                        processed.append({"file_id": getattr(existing, "file_id", file_id), "status": existing.status})
                        continue
                except Exception:
                    pass
                logger.info("s3_ingest bucket=%s key=%s", bucket, key)
                item = ingest_object(file_id=file_id, object_key=key, filename=filename)
                processed.append({"file_id": item.file_id, "status": item.status})
        except Exception:
            logger.exception("ingest_record_failed message_id=%s", message_id)
            if message_id:
                failures.append({"itemIdentifier": message_id})
            else:
                raise
    return {
        "ok": not failures,
        "processed": processed,
        "batchItemFailures": failures,
        "raw": json.dumps(len(processed)),
    }
