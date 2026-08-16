from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "infra" / "template.yaml"
ROOT = Path(__file__).resolve().parents[1]


def test_template_uses_least_privilege_and_required_services():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "AWS::S3::Bucket" in text
    assert "AWS::DynamoDB::Table" in text
    assert "AWS::Serverless::Function" in text
    assert "AWS::SQS::Queue" in text
    assert "AWS::CloudWatch::Alarm" in text
    assert "rekognition:DetectLabels" in text
    assert "transcribe:StartTranscriptionJob" in text
    assert "bedrock:InvokeModel" in text
    assert "BlockPublicAcls: true" in text
    assert "Action: '*'" not in text
    assert "AWS_ACCESS_KEY_ID" not in text
    assert "cloudwatch:namespace: AgentSys" in text
    assert "RetentionInDays: 14" in text
    assert "deadLetterTargetArn" in text
    assert "agentsys-ingest-dlq" in text
    assert "transcribe.amazonaws.com" in text
    assert "category-index" in text
    assert "foundation-model/*" in text
    assert "MediaIngestFailed" in text
    assert "ApproximateNumberOfMessagesVisible" in text
    assert "ReservedConcurrentExecutions: 2" in text
    assert "SSEEnabled: true" in text


def test_no_legacy_local_stack_files():
    leftovers = [
        "config/redis_client.py",
        "config/qdrant_client.py",
        "config/celery_app.py",
        "apps/api/websockets.py",
        "apps/retrieval/engine.py",
        "apps/agent/executor.py",
        "utils/embeddings.py",
        "demo_ui.py",
    ]
    for rel in leftovers:
        assert not (ROOT / rel).exists(), rel
