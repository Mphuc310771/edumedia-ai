from apps.aws.memory import MemoryPlanner
from apps.agent.search import execute_search
from apps.aws.providers import get_runtime


def test_healthcheck_memory_provider(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "HEALTHY"
    assert body["provider"] == "memory"


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
        "/api/v1/media/upload-url",
        json={"filename": "my-dog.jpg", "content_type": "image/jpeg"},
        headers=auth_headers,
    )
    assert upload.status_code == 200
    data = upload.json()
    put = client.put(data["presigned_url"], content=b"fake-jpeg-bytes")
    assert put.status_code == 200

    processed = client.post(
        "/api/v1/media/process",
        json={
            "file_id": data["file_id"],
            "object_key": data["object_key"],
            "filename": "my-dog.jpg",
            "content_type": "image/jpeg",
        },
        headers=auth_headers,
    )
    assert processed.status_code == 202
    assert processed.json()["status"] == "READY"

    status = client.get(f"/api/v1/media/status/{data['file_id']}", headers=auth_headers)
    assert status.json()["status"] == "READY"

    record = get_runtime().catalog.get(data["file_id"])
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
    assert "SQS ingest queue" in (first.get("pipeline") or [])
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


def test_cognito_bearer_token_auth(client):
    # Test Cognito Bearer Token authentication
    headers = {"Authorization": "Bearer cognito-mock-access-token-fcaj"}
    response = client.get("/api/v1/media/items", headers=headers)
    assert response.status_code == 200
