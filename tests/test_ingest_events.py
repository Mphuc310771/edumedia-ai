import json

from apps.lambda_handlers.ingest import handler, iter_s3_objects


def test_iter_direct_s3_record():
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "agentsys-media"},
                    "object": {"key": "uploads/abc.jpg"},
                }
            }
        ]
    }
    assert iter_s3_objects(event) == [("agentsys-media", "uploads/abc.jpg")]


def test_iter_sqs_wrapped_s3_record():
    inner = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "agentsys-media"},
                    "object": {"key": "uploads/lecture%20board.jpg"},
                }
            }
        ]
    }
    event = {"Records": [{"messageId": "m1", "body": json.dumps(inner)}]}
    assert iter_s3_objects(event) == [("agentsys-media", "uploads/lecture board.jpg")]


def test_iter_skips_s3_test_event():
    event = {"Records": [{"body": json.dumps({"Service": "Amazon S3", "Event": "s3:TestEvent"})}]}
    assert iter_s3_objects(event) == []


def test_handler_skips_transcripts_prefix(monkeypatch):
    called = []

    def fake_ingest(**kwargs):
        called.append(kwargs)
        class Rec:
            file_id = kwargs["file_id"]
            status = "READY"
        return Rec()

    monkeypatch.setattr("apps.lambda_handlers.ingest.ingest_object", fake_ingest)
    monkeypatch.setattr("apps.lambda_handlers.ingest.reset_runtime", lambda: None)

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "b"},
                    "object": {"key": "transcripts/job.json"},
                }
            }
        ]
    }
    result = handler(event, None)
    assert called == []
    assert result["processed"] == []
    assert result["ok"] is True


def test_handler_reports_batch_failure(monkeypatch):
    monkeypatch.setattr("apps.lambda_handlers.ingest.reset_runtime", lambda: None)

    def boom(**kwargs):
        raise RuntimeError("rekognition down")

    monkeypatch.setattr("apps.lambda_handlers.ingest.ingest_object", boom)
    event = {
        "Records": [
            {
                "messageId": "bad-1",
                "body": json.dumps(
                    {
                        "Records": [
                            {
                                "s3": {
                                    "bucket": {"name": "b"},
                                    "object": {"key": "uploads/x.jpg"},
                                }
                            }
                        ]
                    }
                ),
            }
        ]
    }
    result = handler(event, None)
    assert result["ok"] is False
    assert result["batchItemFailures"] == [{"itemIdentifier": "bad-1"}]


def test_handler_eventbridge_transcribe_completion():
    event = {
        "source": "aws.transcribe",
        "detail-type": "Transcribe Job State Change",
        "detail": {
            "TranscriptionJobName": "agentsys-uploads-seed-lecture-audio.mp3",
            "TranscriptionJobStatus": "COMPLETED",
        },
    }
    result = handler(event, None)
    assert result["ok"] is True
    assert result.get("source") == "EventBridge"
