import json
import urllib.request
import pytest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from apps.domain import MediaRecord, SearchPlan
from apps.aws.aws_services import (
    _exc_blob,
    _is_daily_token_throttle,
    _is_rate_throttle,
    _bedrock_quota_blocked,
    _bedrock_rate_blocked,
    _mark_bedrock_daily_quota,
    _mark_bedrock_rate_limit,
    _heuristic_search_plan,
    S3ObjectStore,
    DynamoCatalog,
    _FilterHelper,
    RekognitionVision,
    TranscribeSpeech,
    TitanEmbeddings,
    _read_transcript,
    _parse_bedrock_plan_json,
    BedrockPlanner,
    CloudWatchMetrics,
)
from apps.aws import aws_services
from config.settings import settings


def test_heuristic_search_plan():
    plan = _heuristic_search_plan("tìm ảnh toán", "Lý do")
    assert plan.planner_source == "heuristic"
    assert plan.rationale == "Lý do"


def test_exc_helpers():
    class DummyResponse:
        def __init__(self, err):
            self.response = {"Error": err}

    exc1 = ClientError({"Error": {"Code": "ThrottlingException", "Message": "too many requests"}}, "Op")
    exc2 = ClientError({"Error": {"Code": "QuotaException", "Message": "too many tokens per day"}}, "Op")
    exc3 = ValueError("Standard error")

    assert "throttlingexception" in _exc_blob(exc1)
    assert _is_rate_throttle(exc1)
    assert not _is_daily_token_throttle(exc1)

    assert _is_daily_token_throttle(exc2)
    assert not _is_rate_throttle(exc2)

    assert not _is_daily_token_throttle(exc3)
    assert not _is_rate_throttle(exc3)

def test_bedrock_rate_blocking():
    aws_services._BEDROCK_SKIP_UNTIL = 0
    aws_services._BEDROCK_RATE_SKIP_UNTIL = 0
    assert not _bedrock_quota_blocked()
    assert not _bedrock_rate_blocked()

    _mark_bedrock_daily_quota()
    assert _bedrock_quota_blocked()

    _mark_bedrock_rate_limit()
    assert _bedrock_rate_blocked()
    
    # Reset
    aws_services._BEDROCK_SKIP_UNTIL = 0
    aws_services._BEDROCK_RATE_SKIP_UNTIL = 0


def test_s3_object_store_methods(moto_aws_runtime):
    store = S3ObjectStore()
    
    # presign_put
    url = store.presign_put("test.txt", "text/plain")
    assert "test.txt" in url

    # object_uri
    assert store.object_uri("test.txt") == f"s3://{settings.MEDIA_BUCKET}/test.txt"
    
    # get_bytes NoSuchKey
    assert store.get_bytes("non-existent-key") == b""

    # put_bytes and delete_object
    store.put_bytes("to-delete.txt", b"hello", "text/plain")
    assert store.get_bytes("to-delete.txt") == b"hello"
    store.delete_object("to-delete.txt")
    assert store.get_bytes("to-delete.txt") == b""
    store.delete_object("")  # Should do nothing


def test_dynamo_catalog_methods(moto_aws_runtime):
    catalog = DynamoCatalog()
    
    # Put a valid record and a chunk record
    r1 = MediaRecord(
        file_id="valid-1", filename="a.jpg", s3_key="a.jpg", content_type="image/jpeg",
        category="study", media_type="image", size_bytes=10
    )
    catalog.put(r1)
    
    # Direct table access to insert invalid/chunk items
    catalog.table.put_item(Item={"file_id": "chunk#CHUNK#123", "category": "invalid-cat"})
    catalog.table.put_item(Item={"file_id": "parent-1", "parent_file_id": "p", "category": "invalid-cat"})
    catalog.table.put_item(Item={"file_id": "invalid-1", "size_bytes": "not-an-int"})  # Will fail validation

    # get invalid
    assert catalog.get("invalid-1") is None

    # list_all (should skip chunk, parent, invalid)
    all_items = catalog.list_all()
    assert any(i.file_id == "valid-1" for i in all_items)
    assert not any("CHUNK" in i.file_id for i in all_items)
    assert not any(i.file_id == "invalid-1" for i in all_items)
    assert not any(i.file_id == "parent-1" for i in all_items)

    # search via query_by_category
    plan = SearchPlan(category="study")
    study_items = catalog.search(plan)
    assert len(study_items) > 0

    # clear
    catalog.clear()
    assert len(catalog.list_all()) == 0


def test_filter_helper():
    r1 = MediaRecord(
        file_id="1", filename="1.jpg", s3_key="1.jpg", content_type="image/jpeg",
        media_type="image", category="pets", subject="none", summary="dog cat"
    )
    r2 = MediaRecord(
        file_id="2", filename="2.mp4", s3_key="2.mp4", content_type="video/mp4",
        media_type="video", category="study", subject="math", summary="calculus limits"
    )
    
    records = [r1, r2]
    helper = _FilterHelper(records)
    
    # Filter by media_type
    assert len(helper.search(SearchPlan(media_type="video"))) == 1
    
    # Filter by category
    assert len(helper.search(SearchPlan(category="pets"))) == 1
    
    # Filter by subject
    assert len(helper.search(SearchPlan(subject="math"))) == 1
    
    # Filter by keywords
    res = helper.search(SearchPlan(keywords=["calculus"]))
    assert len(res) == 1
    assert res[0].file_id == "2"

def test_rekognition_vision(monkeypatch):
    vision = RekognitionVision()
    
    mock_client = MagicMock()
    mock_client.detect_labels.return_value = {"Labels": [{"Name": "Dog"}]}
    mock_client.detect_text.return_value = {"TextDetections": [{"Type": "LINE", "DetectedText": "Hello"}]}
    monkeypatch.setattr(vision, "client", mock_client)
    
    labels, text = vision.analyze_image("test.jpg")
    assert labels == ["Dog"]
    assert text == "Hello"

def test_transcribe_speech(monkeypatch):
    speech = TranscribeSpeech()
    
    mock_client = MagicMock()
    mock_client.start_transcription_job.return_value = {}
    mock_client.get_transcription_job.side_effect = [
        {"TranscriptionJob": {"TranscriptionJobStatus": "IN_PROGRESS"}},
        {"TranscriptionJob": {"TranscriptionJobStatus": "COMPLETED", "Transcript": {"TranscriptFileUri": "http://test"}}},
        {"TranscriptionJob": {"TranscriptionJobStatus": "COMPLETED", "Transcript": {"TranscriptFileUri": "http://test"}}},
    ]
    monkeypatch.setattr(speech, "client", mock_client)
    monkeypatch.setattr(aws_services, "_read_transcript", lambda uri, key: "Test transcript")
    
    monkeypatch.setattr(aws_services.time, "sleep", lambda x: None) # Speed up wait
    
    job_name = speech.start_job("test.mp3", "mp3", "f1")
    assert job_name.startswith("agentsys--f1--")
    
    res = speech.transcribe("test.mp3", "mp3", "f1")
    assert res == "Test transcript"


def test_titan_embeddings(monkeypatch):
    embed = TitanEmbeddings()
    # Monkeypatch the function that TitanEmbeddings.embed_text calls internally
    monkeypatch.setattr(
        "apps.search.vector_engine.get_titan_embedding",
        lambda text, bedrock_client=None: [0.1, 0.2],
    )
    assert embed.embed_text("test") == [0.1, 0.2]


def test_read_transcript(monkeypatch):
    # S3 path
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: json.dumps({"results": {"transcripts": [{"transcript": "s3 trans"}]}}).encode())}
    monkeypatch.setattr(aws_services, "_client", lambda svc, **kw: mock_s3 if svc == "s3" else MagicMock())
    
    assert _read_transcript("", "key.json") == "s3 trans"

    # HTTPS path
    monkeypatch.setattr(settings, "MEDIA_BUCKET", "")
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"results": {"transcripts": [{"transcript": "http trans"}]}}).encode()
    
    class MockUrlOpen:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return mock_resp
        def __exit__(self, *args): pass
        
    monkeypatch.setattr(urllib.request, "urlopen", MockUrlOpen)
    assert _read_transcript("https://test.com", "") == "http trans"


def test_bedrock_planner(monkeypatch):
    planner = BedrockPlanner()
    mock_client = MagicMock()
    mock_client.converse.return_value = {
        "output": {"message": {"content": [{"text": '{"search_plan": {"keywords": ["test"]}, "rag_answer": {"direct_answer": "Yes"}}'}]}}
    }
    monkeypatch.setattr(planner, "client", mock_client)
    
    plan = planner.plan("test query")
    assert plan.planner_source == "bedrock"
    assert "test" in plan.keywords


def test_cloudwatch_metrics(monkeypatch):
    cw = CloudWatchMetrics()
    mock_client = MagicMock()
    monkeypatch.setattr(cw, "client", mock_client)
    
    cw.emit("TestMetric", 1.0)
    mock_client.put_metric_data.assert_called_once()


def test_bedrock_planner_synthesize(monkeypatch):
    planner = BedrockPlanner()
    mock_client = MagicMock()
    mock_client.converse.return_value = {
        "output": {"message": {"content": [{"text": '{"direct_answer": "Yes", "evidence_snippet": "yes", "source_file": "a.txt"}'}]}}
    }
    monkeypatch.setattr(planner, "client", mock_client)
    
    class DummyHit:
        def __init__(self):
            self.filename = "a.txt"
            self.media_type = "image"
            self.ocr_text = "hello"
    
    ans, ev, src = planner.synthesize_answer("test?", [DummyHit()])
    assert ans == "Yes"

def test_ping_aws_real(monkeypatch):
    import importlib
    import time
    
    # Reload module to bypass the conftest monkeypatch on ping_aws
    from apps.aws import aws_services
    importlib.reload(aws_services)
    
    # Mock all the clients
    mock_sts = MagicMock()
    mock_s3 = MagicMock()
    mock_dynamo = MagicMock()
    mock_dynamo.describe_table.side_effect = ClientError({"Error": {"Code": "AccessDenied", "Message": ""}}, "Op")
    mock_rekog = MagicMock()
    mock_transcribe = MagicMock()
    mock_transcribe.list_transcription_jobs.side_effect = Exception("Fail")
    mock_bedrock = MagicMock()
    
    def mock_client(svc, **kwargs):
        if svc == "sts": return mock_sts
        if svc == "s3": return mock_s3
        if svc == "dynamodb": return mock_dynamo
        if svc == "rekognition": return mock_rekog
        if svc == "transcribe": return mock_transcribe
        if svc == "bedrock": return mock_bedrock
        return MagicMock()
        
    monkeypatch.setattr(aws_services, "_client", mock_client)
    aws_services._PING_CACHE["at"] = 0
    aws_services._PING_CACHE["payload"] = None
    
    res = aws_services.ping_aws(0)
    assert res["status"]["sts"] == "ONLINE"
    assert res["status"]["s3"] == "ONLINE"
    assert res["status"]["dynamodb"] == "UNKNOWN" # Access denied mapped to UNKNOWN
    assert res["status"]["transcribe"] == "OFFLINE"
    
    # Delete DynamoCatalog test
    cat = aws_services.DynamoCatalog()
    # It requires the Moto backend which might not be connected if we mock _client globally,
    # but the catalog fixture uses resource("dynamodb") which is untouched.
    # Actually DynamoCatalog is tested elsewhere, let's just make sure we call delete
    
def test_dynamo_delete(moto_aws_runtime):
    from apps.aws.aws_services import DynamoCatalog
    cat = DynamoCatalog()
    cat.delete("test")

