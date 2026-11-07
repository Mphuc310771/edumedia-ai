import pytest
from apps.aws.providers import get_runtime
from apps.domain import MediaRecord


def test_upload_url_validates_file_extension(client, auth_headers):
    resp = client.post(
        "/api/v1/media/upload-url",
        json={"filename": "malicious.exe", "content_type": "application/x-msdownload"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "không được hỗ trợ" in resp.json()["detail"]


def test_upload_url_rejects_large_files(client, auth_headers):
    # Over 25MB (26MB)
    size_26mb = 26 * 1024 * 1024
    resp = client.post(
        "/api/v1/media/upload-url",
        json={"filename": "huge_lecture.mp4", "content_type": "video/mp4", "size_bytes": size_26mb},
        headers=auth_headers,
    )
    assert resp.status_code == 413
    assert "25MB" in resp.json()["detail"]


def test_upload_url_returns_both_presigned_and_upload_url(client, auth_headers):
    resp = client.post(
        "/api/v1/media/upload-url",
        json={"filename": "board.jpg", "content_type": "image/jpeg", "size_bytes": 1024 * 1024},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "presigned_url" in data
    assert "upload_url" in data
    assert data["presigned_url"] == data["upload_url"]


def test_demo_protected_item_cannot_be_deleted_without_force(client, auth_headers):
    runtime = get_runtime()
    record = MediaRecord(
        file_id="sample_lecture_demo",
        filename="sample_lecture.mp4",
        s3_key="uploads/sample_lecture.mp4",
        media_type="video",
        content_type="video/mp4",
        status="READY",
        is_demo_protected=True,
    )
    runtime.catalog.put(record)

    # Attempt delete without force
    resp = client.delete(f"/api/v1/media/{record.file_id}", headers=auth_headers)
    assert resp.status_code == 403
    assert "bảo vệ" in resp.json()["detail"]

    # Delete with force
    force_headers = dict(auth_headers)
    force_headers["x-admin-force"] = "true"
    resp_force = client.delete(f"/api/v1/media/{record.file_id}", headers=force_headers)
    assert resp_force.status_code == 200
    assert resp_force.json()["file_id"] == record.file_id


def test_clear_all_preserves_demo_protected_items(client, auth_headers):
    runtime = get_runtime()
    demo_rec = MediaRecord(
        file_id="demo_lecture_board",
        filename="demo_lecture.jpg",
        s3_key="uploads/demo_lecture.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        is_demo_protected=True,
    )
    user_rec = MediaRecord(
        file_id="user_uploaded_test",
        filename="my_test_notes.jpg",
        s3_key="uploads/my_test_notes.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        is_demo_protected=False,
    )
    runtime.catalog.put(demo_rec)
    runtime.catalog.put(user_rec)

    # Call /clear
    resp = client.delete("/api/v1/media/clear", headers=auth_headers)
    assert resp.status_code == 200
    assert "cleared" in resp.json()["message"].lower()

    # Demo record should still exist
    assert runtime.catalog.get("demo_lecture_board") is not None
    # User record should be deleted
    assert runtime.catalog.get("user_uploaded_test") is None

    # Cleanup demo record
    runtime.catalog.delete("demo_lecture_board")


def test_query_alias_and_payload_unification(client, auth_headers):
    # Test POST /api/v1/agent/query with {"query": ...}
    resp = client.post(
        "/api/v1/agent/query",
        json={"query": "bài tập ma trận"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["execution_status"] == "COMPLETED"
    assert resp.json()["user_query"] == "bài tập ma trận"
