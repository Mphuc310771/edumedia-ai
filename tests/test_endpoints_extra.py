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
