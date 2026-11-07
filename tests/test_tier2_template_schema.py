"""Tier-2 Map-Reduce regression suite against the EXACT DynamoDB schema of infra/template.yaml.

Background (adversarial audit, P0): the MetadataTable deployed by SAM has a single partition key
(``file_id`` HASH). Chunk rows are therefore stored as ``<id>#CHUNK#0000`` with
``parent_file_id``. The aggregator used to (a) call ``DescribeTable`` implicitly through
``table.key_schema`` (an IAM action the Lambda roles did not hold) and (b) treat the chunk row's
own id as the parent id, which created ghost rows ``<id>#CHUNK#0000#CHUNK#0000`` and left the
parent stuck in ``REFINING 0/N`` forever.

These tests run the real code path (``apply_transcribe_job`` -> DynamoDB Streams INSERT per
chunk -> ``aggregator_lambda.handler``) on a moto table created with the template's key schema,
while ``DescribeTable`` is *denied* exactly like the pre-fix IAM posture.
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import boto3
import pytest
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

import apps.aws.providers as providers
from apps.aws.aws_services import DynamoCatalog, S3ObjectStore
from apps.aws.providers import Runtime
from apps.domain import MediaRecord
from apps.workers.ingestion import apply_transcribe_job
from config.settings import settings
from pipeline.aggregator_lambda import extract_file_id, handler
from tests.fakes import StubPlanner, StubVision

TEMPLATE = Path(__file__).resolve().parents[1] / "infra" / "template.yaml"
GHOST_PATTERN = re.compile(r"#CHUNK#\d{4}#CHUNK#")

# --- Mirrors infra/template.yaml -> Resources.MetadataTable --------------------------------
TEMPLATE_KEY_SCHEMA = [{"AttributeName": "file_id", "KeyType": "HASH"}]
TEMPLATE_ATTRIBUTE_DEFINITIONS = [
    {"AttributeName": "file_id", "AttributeType": "S"},
    {"AttributeName": "category", "AttributeType": "S"},
]
TEMPLATE_GSI = [
    {
        "IndexName": "category-index",
        "KeySchema": [{"AttributeName": "category", "KeyType": "HASH"}],
        "Projection": {"ProjectionType": "ALL"},
    }
]

_SERIALIZER = TypeSerializer()


# --- helpers -------------------------------------------------------------------------------
class PayloadSpeech:
    """Speech stub returning a fixed Amazon Transcribe JSON payload for read_job_payload()."""

    def __init__(self, payload: dict):
        self.payload = payload

    def read_job_payload(self, job_name: str) -> dict:
        return self.payload


class RecordingMetrics:
    def __init__(self):
        self.calls: list[tuple[str, float]] = []

    def emit(self, name: str, value: float, unit: str = "Count") -> None:
        self.calls.append((name, value))


def _build_transcribe_payload(n_sentences: int = 66, sentence_period: float = 10.0) -> dict:
    """Synthetic Transcribe output: ``n_sentences`` short sentences, one every ``sentence_period``s.

    66 x 10 s = 660 s of speech -> chunk_transcribe_json() (5-10 min windows) yields >= 2 chunks.
    """
    items: list[dict] = []
    transcript_parts: list[str] = []
    for i in range(n_sentences):
        base = i * sentence_period
        words = [f"Cau{i}", "noi", "dung", "giang"]
        for k, word in enumerate(words):
            start = base + k * 1.5
            items.append(
                {
                    "type": "pronunciation",
                    "start_time": f"{start:.2f}",
                    "end_time": f"{start + 1.0:.2f}",
                    "alternatives": [{"content": word, "confidence": "0.99"}],
                }
            )
        items.append({"type": "punctuation", "alternatives": [{"content": ".", "confidence": "0.0"}]})
        transcript_parts.append(" ".join(words) + ".")
    return {
        "jobName": "synthetic",
        "results": {"transcripts": [{"transcript": " ".join(transcript_parts)}], "items": items},
    }


def _stream_event(item: dict, event_name: str, seq: str) -> dict:
    """Wrap a stored item into a DynamoDB Streams Lambda event (NewImage in DynamoDB JSON)."""
    image = _SERIALIZER.serialize(item)["M"]
    return {
        "Records": [
            {
                "eventID": f"evt-{seq}",
                "eventName": event_name,
                "dynamodb": {"SequenceNumber": seq, "NewImage": image},
            }
        ]
    }


def _get(table, file_id: str) -> dict:
    return table.get_item(Key={"file_id": file_id}, ConsistentRead=True).get("Item") or {}


def _all_items(table) -> list[dict]:
    items: list[dict] = []
    kwargs: dict = {}
    while True:
        page = table.scan(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _assert_no_ghosts(table) -> None:
    for item in _all_items(table):
        fid = str(item["file_id"])
        assert not GHOST_PATTERN.search(fid), f"ghost row created: {fid}"
        if "#CHUNK#" in fid:
            assert "chunk_index" in item and item.get("parent_file_id"), f"malformed chunk row: {fid}"


# --- fixtures ------------------------------------------------------------------------------
@pytest.fixture
def tier2_env(monkeypatch):
    """Moto table with the template's key schema + a runtime whose catalog points at it.

    ``DescribeTable`` is denied on the table's client to reproduce the pre-fix IAM posture of
    IngestFunction / AggregatorFunction: the whole pipeline must complete without it.
    """
    table_name = "AgentSysMediaMetadata-tier2-regression"
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    dynamodb.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=TEMPLATE_KEY_SCHEMA,
        AttributeDefinitions=TEMPLATE_ATTRIBUTE_DEFINITIONS,
        GlobalSecondaryIndexes=TEMPLATE_GSI,
    )
    monkeypatch.setattr(settings, "METADATA_TABLE", table_name)

    catalog = DynamoCatalog()
    api_calls: list[str] = []
    events = catalog.table.meta.client.meta.events
    events.register("before-call.dynamodb", lambda **kw: api_calls.append(kw["model"].name))

    def deny_describe_table(**_kw):
        raise ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "assumed-role/agentsys-IngestFunctionRole is not authorized to perform: dynamodb:DescribeTable",
                }
            },
            "DescribeTable",
        )

    events.register("before-call.dynamodb.DescribeTable", deny_describe_table)

    metrics = RecordingMetrics()
    runtime = Runtime(
        catalog=catalog,
        store=S3ObjectStore(),
        vision=StubVision(),
        speech=PayloadSpeech(_build_transcribe_payload()),
        planner=StubPlanner(),  # .client is None -> deterministic chunk summaries (no Bedrock)
        metrics=metrics,
        provider="aws",
    )
    monkeypatch.setattr(providers, "_RUNTIME", runtime)
    # Separate, un-hooked Table resource for test-side reads so api_calls only records what the
    # pipeline itself issues (lets the tests assert "no Scan / no DescribeTable" precisely).
    probe = boto3.resource("dynamodb", region_name=settings.AWS_REGION).Table(table_name)
    return SimpleNamespace(
        table=catalog.table, probe=probe, catalog=catalog, runtime=runtime, api_calls=api_calls, metrics=metrics
    )


# --- tests ---------------------------------------------------------------------------------
def test_schema_constants_mirror_template():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "- AttributeName: file_id\n          KeyType: HASH" in text
    assert "KeyType: RANGE" not in text, "template gained a sort key: update chunk_state key layout + this suite"
    assert "IndexName: category-index" in text


def test_extract_file_id_never_uses_a_chunk_id_as_parent():
    # 1. parent_file_id wins (what save_chunks_batch writes on every chunk row)
    assert extract_file_id({"file_id": "abc#CHUNK#0000", "parent_file_id": "abc"}) == "abc"
    # 2. legacy PK attribute
    assert extract_file_id({"file_id": "abc#CHUNK#0000", "PK": "FILE#abc", "SK": "CHUNK#0000"}) == "abc"
    # 3. genuine parent row
    assert extract_file_id({"file_id": "abc", "total_chunks": 2}) == "abc"
    # 4. orphan / ghost rows are skipped, never promoted to a parent id
    assert extract_file_id({"file_id": "abc#CHUNK#0001"}) is None
    assert extract_file_id({"file_id": "abc#CHUNK#0000#CHUNK#0000"}) is None
    assert extract_file_id({"PK": "FILE#abc#CHUNK#0000"}) is None
    assert extract_file_id({}) is None


def test_tier2_map_reduce_completes_on_template_schema(tier2_env):
    env = tier2_env
    file_id = "lec-2026-09-21-os"
    job_name = f"agentsys--{file_id}--uploads_{file_id}_mp3"
    env.catalog.put(
        MediaRecord(
            file_id=file_id,
            filename=f"{file_id}.mp3",
            s3_key=f"uploads/{file_id}.mp3",
            media_type="audio",
            content_type="audio/mpeg",
            status="INDEXING",
            transcribe_job_name=job_name,
            analysis_source="transcribe-indexing",
        )
    )
    env.api_calls.clear()

    # ---- Phase 1: Transcribe COMPLETED callback -> Tier-1 provisional + Tier-2 init ----
    result = apply_transcribe_job(job_name, "COMPLETED")
    assert result == {"ok": True, "file_id": file_id, "status": "READY", "source": "EventBridge"}

    parent = _get(env.probe, file_id)
    total = int(parent["total_chunks"])
    assert total >= 2, "synthetic lecture must span several 5-10 minute chunks"
    assert parent["status"] == "READY"
    assert parent["pipeline_status"] == "REFINING"
    assert int(parent["chunks_completed"]) == 0
    assert parent["transcript"] and parent["summary"], "Tier-1 fields must survive the READY flip"
    assert "error" not in parent

    chunks = [_get(env.probe, f"{file_id}#CHUNK#{i:04d}") for i in range(total)]
    assert all(c and c["status"] == "PENDING" and c["parent_file_id"] == file_id for c in chunks)
    assert [int(c["chunk_index"]) for c in chunks] == list(range(total))
    _assert_no_ghosts(env.probe)
    assert "DescribeTable" not in env.api_calls

    # ---- Phase 2: one DynamoDB Streams INSERT per chunk row -> real Lambda handler ----
    expected_summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        # StubPlanner.client is None -> _refine_chunk_with_bedrock falls back to the first sentence
        expected_summaries.append(chunk["text"].split(". ")[0].strip())

        response = handler(_stream_event(chunk, "INSERT", seq=str(100 + i)), context=None)
        assert response["ok"] is True, response
        assert "batchItemFailures" not in response

        parent = _get(env.probe, file_id)
        assert int(parent["chunks_completed"]) == i + 1, "counter must increment exactly once per chunk"
        assert int(parent["total_chunks"]) == total
        chunk_row = _get(env.probe, chunk["file_id"])
        assert chunk_row["status"] == "DONE" and chunk_row["summary"] == expected_summaries[-1]
        _assert_no_ghosts(env.probe)
        if i < total - 1:
            assert parent["pipeline_status"] == "REFINING"

    parent = _get(env.probe, file_id)
    assert parent["pipeline_status"] == "REFINED_COMPLETED"
    assert parent["summary"] == " · ".join(expected_summaries)
    assert int(parent["chunks_completed"]) == total == int(parent["total_chunks"])
    assert parent["status"] == "READY"
    assert "DescribeTable" not in env.api_calls, "pipeline must not depend on DescribeTable"
    # Chunk rows are fetched by key (BatchGetItem); the aggregator must never Scan the table.
    assert "Scan" not in env.api_calls, "aggregator issued a table Scan"
    assert "BatchGetItem" in env.api_calls

    # The catalog projection (what the API serves) sees the refined summary on the SAME item.
    record = env.catalog.get(file_id)
    assert record is not None
    assert record.status == "READY"
    assert record.pipeline_status == "REFINED_COMPLETED"
    assert record.summary == parent["summary"]

    # Exactly one MediaIngested emission, none failed.
    assert env.metrics.calls.count(("MediaIngested", 1)) == 1
    assert ("MediaIngestFailed", 1) not in env.metrics.calls

    # ---- Phase 3: at-least-once redelivery of the last chunk INSERT is a no-op ----
    replay = handler(_stream_event(chunks[-1], "INSERT", seq="999"), context=None)
    assert replay["ok"] is True
    parent_after = _get(env.probe, file_id)
    assert int(parent_after["chunks_completed"]) == total, "duplicate delivery must not double-count"
    assert parent_after["summary"] == parent["summary"]
    assert parent_after["updated_at"] == parent["updated_at"], "finalised parent must not be rewritten"
    _assert_no_ghosts(env.probe)

    # ---- Phase 4: the parent MODIFY emitted by finalisation does not trigger another reduce ----
    done = handler(_stream_event(parent_after, "MODIFY", seq="1000"), context=None)
    assert done["ok"] is True and done["processed_count"] == 0

    # Table hygiene: exactly 1 parent + N chunk rows, nothing else.
    ids = sorted(str(item["file_id"]) for item in _all_items(env.probe))
    assert ids == sorted([file_id] + [f"{file_id}#CHUNK#{i:04d}" for i in range(total)])


def test_chunk_event_for_uninitialised_parent_creates_nothing(tier2_env):
    """A stray chunk INSERT whose parent has no Tier-2 state must neither ghost nor finalise."""
    env = tier2_env
    file_id = "orphan-parent"
    env.catalog.put(
        MediaRecord(
            file_id=file_id,
            filename="orphan.mp3",
            s3_key="uploads/orphan.mp3",
            media_type="audio",
            content_type="audio/mpeg",
            status="READY",
        )
    )
    stray_chunk = {
        "file_id": f"{file_id}#CHUNK#0000",
        "parent_file_id": file_id,
        "PK": f"FILE#{file_id}",
        "SK": "CHUNK#0000",
        "chunk_index": 0,
        "status": "PENDING",
        "text": "Noi dung. Them nua.",
        "summary": "",
    }
    env.probe.put_item(Item=stray_chunk)

    response = handler(_stream_event(stray_chunk, "INSERT", seq="1"), context=None)
    assert response["ok"] is True

    parent = _get(env.probe, file_id)
    assert "chunks_completed" not in parent and "total_chunks" not in parent
    assert parent.get("pipeline_status") != "REFINED_COMPLETED"
    assert _get(env.probe, f"{file_id}#CHUNK#0000")["status"] == "DONE"  # chunk itself is refined
    _assert_no_ghosts(env.probe)
    assert "DescribeTable" not in env.api_calls
