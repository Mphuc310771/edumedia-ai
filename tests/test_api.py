from apps.agent.search import execute_search
from apps.aws.providers import get_runtime
from config.settings import settings


def test_healthcheck_aws_provider(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    body = response.json()
    assert body["status"] == "HEALTHY"
    assert body["provider"] == "aws"
    assert body["components"]["rekognition"] == "ONLINE"
    assert body["ingest_mode"] == "sync"


def test_upload_url_unauthorized(client):
    response = client.post(
        "/api/v1/media/upload-url",
        json={"filename": "sample.jpg", "content_type": "image/jpeg"},
        headers={"X-API-Key": "invalid-key"},
    )
    assert response.status_code == 401


def test_list_seed_items(client, auth_headers):
    response = client.get("/api/v1/media/items", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 6
    assert any("Round Robin" in (item.get("transcript") or "") for item in items)


def test_upload_and_process_image(client, auth_headers):
    upload = client.post(
        "/api/v1/media/upload",
        files={"file": ("my-dog.jpg", b"fake-jpeg-bytes", "image/jpeg")},
        headers=auth_headers,
    )
    assert upload.status_code == 200
    data = upload.json()
    assert data["status"] == "READY"
    assert data["filename"] == "my-dog.jpg"

    status = client.get(f"/api/v1/media/status/{data['id']}", headers=auth_headers)
    assert status.json()["status"] == "READY"

    record = get_runtime().catalog.get(data["id"])
    assert record is not None
    assert "Dog" in record.labels or record.category == "pets"


def test_agent_query_finds_exam_tip(client, auth_headers):
    response = client.post(
        "/api/v1/media/agent/query",
        json={"user_query": "Tìm đoạn thầy dặn thi cuối kỳ"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["execution_status"] == "COMPLETED"
    assert body["results"]
    first = body["results"][0]
    assert first.get("matchedFields")
    transcripts = " ".join(item.get("transcript") or "" for item in body["results"])
    assert "Round Robin" in transcripts or "thi cuối kỳ" in transcripts.lower()


def test_upload_batch_multiple_files(client, auth_headers):
    files = [
        ("files", ("batch-1.jpg", b"fake-jpg-content-1", "image/jpeg")),
        ("files", ("batch-2.jpg", b"fake-jpg-content-2", "image/jpeg")),
    ]
    response = client.post("/api/v1/media/upload-batch", files=files, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["filename"] == "batch-1.jpg"
    assert data[1]["filename"] == "batch-2.jpg"


def test_list_requires_auth(client):
    response = client.get("/api/v1/media/items")
    assert response.status_code == 401


def test_login_issues_session_token(client):
    password = settings.ADMIN_PASSWORD or settings.ADMIN_API_KEY or "test-key"
    response = client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME or "admin", "password": password},
    )
    assert response.status_code == 200
    token = response.json()["token"]
    listed = client.get("/api/v1/media/items", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    assert len(listed.json()) >= 6


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_cognito_bearer_token_auth(client):
    headers = {"Authorization": "Bearer cognito-mock-access-token-fcaj"}
    response = client.get("/api/v1/media/items", headers=headers)
    assert response.status_code == 401


def test_list_uses_thumbnail_not_original(client, auth_headers):
    items = client.get("/api/v1/media/items", headers=auth_headers).json()
    dog = next(item for item in items if item["id"] == "seed-golden-dog")
    assert dog["url"] == ""
    assert not dog.get("thumbnailUrl")
    original = client.get("/api/v1/media/items/seed-golden-dog/url", headers=auth_headers)
    assert original.status_code == 200
    assert "seed-golden-dog" in original.json()["url"]


def test_upload_image_writes_thumbnail(client, auth_headers):
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (64, 48), (30, 90, 160)).save(buffer, format="JPEG")
    upload = client.post(
        "/api/v1/media/upload",
        files={"file": ("lecture-board.jpg", buffer.getvalue(), "image/jpeg")},
        headers=auth_headers,
    )
    assert upload.status_code == 200
    data = upload.json()
    record = get_runtime().catalog.get(data["id"])
    assert record is not None
    assert record.thumb_key == f"thumbs/{data['id']}.jpg"
    listed = next(item for item in client.get("/api/v1/media/items", headers=auth_headers).json() if item["id"] == data["id"])
    assert listed["thumbnailUrl"]
    assert listed["url"] == listed["thumbnailUrl"]
    assert "thumbs/" in listed["thumbnailUrl"]


def test_delete_removes_catalog_and_s3_objects(client, auth_headers):
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(buffer, format="JPEG")
    upload = client.post(
        "/api/v1/media/upload",
        files={"file": ("lecture-board.jpg", buffer.getvalue(), "image/jpeg")},
        headers=auth_headers,
    )
    file_id = upload.json()["id"]
    record = get_runtime().catalog.get(file_id)
    assert record is not None
    store = get_runtime().store
    assert store.get_bytes(record.s3_key)
    assert store.get_bytes(record.thumb_key)

    deleted = client.delete(f"/api/v1/media/{file_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert get_runtime().catalog.get(file_id) is None
    assert store.get_bytes(record.s3_key) == b""
    assert store.get_bytes(record.thumb_key) == b""
