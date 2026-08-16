import json
import logging
from typing import Any, List, Tuple
from urllib.parse import unquote_plus

from apps.aws.providers import reset_runtime
from apps.workers.ingestion import ingest_object

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


def handler(event, context):
    reset_runtime()
    failures = []
    processed = []
    for record in event.get("Records") or []:
        message_id = record.get("messageId") or ""
        try:
            objects = iter_s3_objects({"Records": [record]})
            for bucket, key in objects:
                if not key.startswith("uploads/"):
                    logger.info("skip_non_upload bucket=%s key=%s", bucket, key)
                    continue
                filename = key.rsplit("/", 1)[-1]
                file_id = filename.split(".")[0]
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
