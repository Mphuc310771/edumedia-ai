"""Additional tests for apps.api.endpoints and apps.api.main to increase coverage.

Targets uncovered lines in:
- endpoints.py: _human_size, _presign, _purge_objects, generate_upload_url,
  trigger_media_processing, reprocess_item, clear_all_items, _list_records error path
- main.py: lifespan startup, global_exception_handler, healthcheck degraded/offline paths
"""
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image


# ──────────────────────────────────────────────────────────
# endpoints.py helpers
# ──────────────────────────────────────────────────────────

def test_human_size_zero():
    from apps.api.endpoints import _human_size
    assert _human_size(0) == "—"


def test_human_size_bytes():
    from apps.api.endpoints import _human_size
    assert _human_size(512) == "512 B"


def test_human_size_kb():
    from apps.api.endpoints import _human_size
    result = _human_size(2048)
    assert "KB" in result


def test_human_size_mb():
    from apps.api.endpoints import _human_size
    result = _human_size(5 * 1024 * 1024)
    assert "MB" in result


def test_human_size_gb():
    from apps.api.endpoints import _human_size
    result = _human_size(3 * 1024 ** 3)
    assert "GB" in result


def test_presign_empty_key():
    from apps.api.endpoints import _presign
    assert _presign("") == ""


def test_make_file_id_deterministic():
    from apps.api.endpoints import make_file_id
    fid1 = make_file_id("test.jpg", b"data")
    fid2 = make_file_id("test.jpg", b"data")
    assert fid1 == fid2
    assert "test.jpg" in fid1 or "test_jpg" in fid1


def test_make_file_id_sanitizes():
    from apps.api.endpoints import make_file_id
    fid = make_file_id("ảnh chụp bảng.jpg", b"x")
    assert len(fid) <= 50


# ──────────────────────────────────────────────────────────
# Endpoints via TestClient
# ──────────────────────────────────────────────────────────

def test_upload_url_returns_presigned(client, auth_headers):
    resp = client.post(
        "/api/v1/media/upload-url",
        json={"filename": "sample.jpg", "content_type": "image/jpeg"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_id"]
    assert body["presigned_url"]
    assert body["object_key"].startswith("uploads/")


def test_process_endpoint_returns_202(client, auth_headers):
    resp = client.post(
        "/api/v1/media/process",
        json={"file_id": "proc-test-1", "content_type": "image/jpeg", "filename": "proc.jpg"},
        headers=auth_headers,
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "INDEXING"
    assert body["file_id"] == "proc-test-1"


def test_status_unknown_file_id(client, auth_headers):
    resp = client.get("/api/v1/media/status/nonexistent-id-999", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "UNKNOWN"


def test_reprocess_not_found(client, auth_headers):
    resp = client.post("/api/v1/media/reprocess/nonexistent-file-id", headers=auth_headers)
    assert resp.status_code == 404


def test_reprocess_existing_file(client, auth_headers):
    # Upload a file first
    buffer = BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(buffer, format="JPEG")
    upload = client.post(
        "/api/v1/media/upload",
        files={"file": ("reprocess-test.jpg", buffer.getvalue(), "image/jpeg")},
        headers=auth_headers,
    )
    file_id = upload.json()["id"]
    resp = client.post(f"/api/v1/media/reprocess/{file_id}", headers=auth_headers)
    assert resp.status_code == 202
    assert resp.json()["status"] == "INDEXING"


def test_item_content_url_not_found(client, auth_headers):
    resp = client.get("/api/v1/media/items/nonexistent-id/url", headers=auth_headers)
    assert resp.status_code == 404


def test_clear_all_items(client, auth_headers):
    resp = client.delete("/api/v1/media/clear", headers=auth_headers)
    assert resp.status_code == 200
    assert "cleared" in resp.json()["message"].lower()
    # After clearing, list should be empty
    items = client.get("/api/v1/media/items", headers=auth_headers).json()
    assert len(items) == 0


def test_delete_not_found(client, auth_headers):
    resp = client.delete("/api/v1/media/nonexistent-id", headers=auth_headers)
    assert resp.status_code == 404


# ──────────────────────────────────────────────────────────
# main.py coverage
# ──────────────────────────────────────────────────────────

def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_healthcheck_degraded_when_service_offline(client, monkeypatch):
    monkeypatch.setattr(
        "apps.aws.aws_services.ping_aws",
        lambda ttl_seconds=0: {
            "status": {
                "sts": "ONLINE", "s3": "ONLINE", "dynamodb": "ONLINE",
                "rekognition": "ONLINE", "transcribe": "OFFLINE", "bedrock": "ONLINE",
            },
            "errors": {"transcribe": "SubscriptionRequired: service not enabled"},
        },
    )
    resp = client.get("/health")
    body = resp.json()
    assert body["status"] == "DEGRADED"
    assert "Transcribe" in body.get("message", "")
    assert "transcribe" in body.get("component_errors", {})


def test_healthcheck_degraded_non_transcribe(client, monkeypatch):
    monkeypatch.setattr(
        "apps.aws.aws_services.ping_aws",
        lambda ttl_seconds=0: {
            "status": {
                "sts": "ONLINE", "s3": "OFFLINE", "dynamodb": "ONLINE",
                "rekognition": "ONLINE", "transcribe": "ONLINE", "bedrock": "ONLINE",
            },
            "errors": {"s3": "NoSuchBucket"},
        },
    )
    resp = client.get("/health")
    body = resp.json()
    assert body["status"] == "DEGRADED"
    # No special transcribe message when transcribe is online
    assert "message" not in body


def test_global_exception_handler(monkeypatch):
    """Test that unhandled exceptions return 500 with request_id."""
    from fastapi.testclient import TestClient
    from apps.api.main import app

    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "apps.aws.aws_services.ping_aws", _boom,
    )
    error_client = TestClient(app, raise_server_exceptions=False)
    resp = error_client.get("/health")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] is True
    assert body["request_id"]


def test_process_endpoint_enqueues_sqs(client, auth_headers, monkeypatch):
    """Test that /process sends an SQS message instead of BackgroundTasks."""
    enqueued_messages = []
    monkeypatch.setattr(
        "apps.aws.aws_services.SQSQueue.send_message",
        lambda self, msg: enqueued_messages.append(msg) or True,
    )
    resp = client.post(
        "/api/v1/media/process",
        json={"file_id": "proc-sqs-test", "content_type": "image/jpeg", "filename": "proc.jpg"},
        headers=auth_headers,
    )
    assert resp.status_code == 202
    assert len(enqueued_messages) == 1
    assert enqueued_messages[0]["action"] == "process"
    assert enqueued_messages[0]["file_id"] == "proc-sqs-test"
    assert enqueued_messages[0]["object_key"] == "uploads/proc-sqs-test"


def test_reprocess_endpoint_enqueues_sqs(client, auth_headers, monkeypatch):
    """Test that /reprocess sends an SQS message instead of BackgroundTasks."""
    from apps.domain import MediaRecord
    from apps.aws.providers import get_runtime

    runtime = get_runtime()
    record = MediaRecord(
        file_id="reproc-sqs-test",
        filename="reproc.jpg",
        s3_key="uploads/reproc.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="FAILED",
    )
    runtime.catalog.put(record)

    enqueued_messages = []
    monkeypatch.setattr(
        "apps.aws.aws_services.SQSQueue.send_message",
        lambda self, msg: enqueued_messages.append(msg) or True,
    )

    resp = client.post("/api/v1/media/reprocess/reproc-sqs-test", headers=auth_headers)
    assert resp.status_code == 202
    assert len(enqueued_messages) == 1
    assert enqueued_messages[0]["action"] == "reprocess"
    assert enqueued_messages[0]["file_id"] == "reproc-sqs-test"


def test_ingest_handler_direct_sqs_action():
    """Test that IngestHandler consumes direct SQS action messages."""
    import json
    from apps.lambda_handlers.ingest import handler

    event = {
        "Records": [
            {
                "messageId": "msg-sqs-direct",
                "body": json.dumps({
                    "action": "process",
                    "file_id": "direct-sqs-item",
                    "object_key": "uploads/direct-sqs-item.jpg",
                    "filename": "direct-sqs-item.jpg",
                    "content_type": "image/jpeg",
                }),
            }
        ]
    }
    res = handler(event, None)
    assert res["ok"] is True
    assert len(res["processed"]) == 1
    assert res["processed"][0]["file_id"] == "direct-sqs-item"


def test_get_real_client_ip():
    from apps.api.rate_limit import get_real_client_ip
    from starlette.requests import Request

    # Case 1: X-Forwarded-For with multiple proxies
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.195, 70.41.3.18, 150.172.238.178")],
        "client": ("10.0.0.1", 12345),
    }
    req = Request(scope)
    assert get_real_client_ip(req) == "203.0.113.195"

    # Case 2: No X-Forwarded-For, fallback to client.host
    scope2 = {
        "type": "http",
        "headers": [],
        "client": ("192.168.1.100", 12345),
    }
    req2 = Request(scope2)
    assert get_real_client_ip(req2) == "192.168.1.100"

    # Case 3: Neither present, fallback to 127.0.0.1
    scope3 = {
        "type": "http",
        "headers": [],
        "client": None,
    }
    req3 = Request(scope3)
    assert get_real_client_ip(req3) == "127.0.0.1"


def test_fold_text_null_bytes():
    from apps.classify.text import fold_text

    assert fold_text("Tiếng\x00Việt") == "tieng viet"
    assert fold_text("\x00\x00abc\x00def\x00") == "abc def"
    assert fold_text(None) == ""


def test_large_transcript_s3_offloading():
    import json
    from apps.aws.providers import get_runtime
    from apps.domain import MediaRecord
    from apps.workers.ingestion import _offload_transcript_if_large

    runtime = get_runtime()
    record = MediaRecord(
        file_id="large-audio-test",
        filename="lecture.mp3",
        s3_key="uploads/large-audio-test.mp3",
        media_type="audio",
        content_type="audio/mpeg",
        status="INDEXING",
    )
    # Generate transcript > 250KB
    large_text = "Học phần Kiến trúc máy tính và Hệ điều hành. " * 6000
    assert len(large_text.encode("utf-8")) > 250 * 1024

    truncated = _offload_transcript_if_large(record, large_text, runtime)
    assert record.has_extended_transcript is True
    assert record.transcript_s3_uri is not None
    assert "transcripts/raw/large-audio-test.json" in record.transcript_s3_uri
    assert len(truncated) <= 16000
    assert "[Full transcript stored in S3]" in truncated

    # Verify S3 store received the raw content
    s3_key = "transcripts/raw/large-audio-test.json"
    stored_bytes = runtime.store.get_bytes(s3_key)
    assert len(stored_bytes) > 250 * 1024
    data = json.loads(stored_bytes.decode("utf-8"))
    assert data["file_id"] == "large-audio-test"
    assert data["transcript"] == large_text

