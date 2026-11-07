import pytest

from pipeline.chunking import TranscriptChunk
from pipeline.chunk_state import (
    ChunkRecord,
    MemoryChunkStore,
    get_file_chunks,
    init_file_pipeline_state,
    mark_chunk_completed,
    mark_chunk_failed,
    save_chunks_batch,
)


def test_chunk_lifecycle_and_atomic_counter():
    store = MemoryChunkStore()
    file_id = "test-audio-001"

    chunks = [
        TranscriptChunk(
            chunk_id=f"{file_id}-chunk-0000",
            chunk_index=0,
            file_id=file_id,
            start_time=0.0,
            end_time=300.0,
            text="Đoạn 1 bài giảng hệ điều hành",
            item_count=50,
        ),
        TranscriptChunk(
            chunk_id=f"{file_id}-chunk-0001",
            chunk_index=1,
            file_id=file_id,
            start_time=300.0,
            end_time=600.0,
            text="Đoạn 2 thuật toán Round Robin",
            item_count=60,
        ),
        TranscriptChunk(
            chunk_id=f"{file_id}-chunk-0002",
            chunk_index=2,
            file_id=file_id,
            start_time=600.0,
            end_time=900.0,
            text="Đoạn 3 phân trang Paging và Virtual Memory",
            item_count=70,
        ),
    ]

    # 1. Initialize file state
    init_file_pipeline_state(store, file_id=file_id, total_chunks=len(chunks), provisional_summary={"provisional": "ok"})
    file_meta = store.get_file(file_id)
    assert file_meta["total_chunks"] == 3
    assert file_meta["chunks_completed"] == 0
    assert file_meta["pipeline_status"] == "REFINING"

    # 2. Save chunks
    save_chunks_batch(store, file_id=file_id, chunks=chunks)
    saved = get_file_chunks(store, file_id=file_id)
    assert len(saved) == 3
    assert all(c["status"] == "PENDING" for c in saved)

    # 3. Complete chunk 1 (out of order, e.g. worker 1 finishes first)
    res1 = mark_chunk_completed(store, file_id=file_id, chunk_index=1, chunk_summary="Tóm tắt đoạn 2: Round Robin")
    assert res1["chunks_completed"] == 1
    assert res1["total_chunks"] == 3

    # 4. Complete chunk 0
    res0 = mark_chunk_completed(store, file_id=file_id, chunk_index=0, chunk_summary="Tóm tắt đoạn 1: Giới thiệu")
    assert res0["chunks_completed"] == 2

    # 5. Complete chunk 2
    res2 = mark_chunk_completed(store, file_id=file_id, chunk_index=2, chunk_summary="Tóm tắt đoạn 3: Virtual Memory")
    assert res2["chunks_completed"] == 3

    # 6. Verify retrieved chunks are in strict index order (0, 1, 2)
    final_chunks = get_file_chunks(store, file_id=file_id)
    assert [c["chunk_index"] for c in final_chunks] == [0, 1, 2]
    assert all(c["status"] == "DONE" for c in final_chunks)


def test_chunk_failure_and_retry_tracking():
    store = MemoryChunkStore()
    file_id = "test-fail-002"

    chunk = TranscriptChunk(
        chunk_id=f"{file_id}-chunk-0000",
        chunk_index=0,
        file_id=file_id,
        start_time=0.0,
        end_time=100.0,
        text="Đoạn lỗi",
        item_count=10,
    )
    init_file_pipeline_state(store, file_id=file_id, total_chunks=1)
    save_chunks_batch(store, file_id=file_id, chunks=[chunk])

    # Record first failure
    res = mark_chunk_failed(store, file_id=file_id, chunk_index=0, error_msg="Bedrock ThrottlingException")
    assert res["status"] == "FAILED"
    assert res["retry_count"] == 1
    assert "Throttling" in res["last_error"]

    # Record second retry failure
    res2 = mark_chunk_failed(store, file_id=file_id, chunk_index=0, error_msg="TimeoutError")
    assert res2["retry_count"] == 2
    assert "Timeout" in res2["last_error"]


# ------------------------------------------------------------------------------------------
# DynamoDB reader (moto; mock_aws is active through the autouse conftest fixture)
# ------------------------------------------------------------------------------------------
def _template_schema_table(name: str):
    import boto3

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName=name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "file_id", "KeyType": "HASH"}],  # infra/template.yaml
        AttributeDefinitions=[{"AttributeName": "file_id", "AttributeType": "S"}],
    )
    calls: list[str] = []
    table.meta.client.meta.events.register("before-call.dynamodb", lambda **kw: calls.append(kw["model"].name))
    return table, calls


def test_get_file_chunks_uses_keyed_batch_reads_not_scan():
    table, calls = _template_schema_table("ChunkReaderKeyed")
    file_id = "long-lecture"
    total = 120  # > 100 -> exercises the BatchGetItem 100-key paging
    table.put_item(Item={"file_id": file_id, "total_chunks": total, "chunks_completed": 0, "pipeline_status": "REFINING"})
    for i in reversed(range(total)):  # write out of order on purpose
        table.put_item(
            Item={"file_id": f"{file_id}#CHUNK#{i:04d}", "parent_file_id": file_id, "chunk_index": i, "status": "PENDING", "text": f"c{i}"}
        )
    # Ghost/legacy row that must never be treated as a chunk
    table.put_item(Item={"file_id": f"{file_id}#CHUNK#0000#CHUNK#0000", "status": "DONE"})
    calls.clear()

    chunks = get_file_chunks(table, file_id)

    assert [int(c["chunk_index"]) for c in chunks] == list(range(total))
    assert all(c["parent_file_id"] == file_id for c in chunks)
    assert calls.count("BatchGetItem") == 2  # 100 + 20 keys
    assert "Scan" not in calls and "DescribeTable" not in calls


def test_get_file_chunks_falls_back_to_bounded_scan_without_total_chunks():
    from pipeline import chunk_state

    table, calls = _template_schema_table("ChunkReaderFallback")
    file_id = "legacy-lecture"
    table.put_item(Item={"file_id": file_id, "status": "READY"})  # legacy parent: no Tier-2 counters
    for i in range(3):
        table.put_item(Item={"file_id": f"{file_id}#CHUNK#{i:04d}", "parent_file_id": file_id, "chunk_index": i, "status": "DONE"})
    # Unrelated bulk rows so the scan has to paginate under the small page limit
    for i in range(600):
        table.put_item(Item={"file_id": f"other-{i:04d}", "status": "READY"})
    calls.clear()

    chunks = get_file_chunks(table, file_id)

    assert [int(c["chunk_index"]) for c in chunks] == [0, 1, 2]
    assert "BatchGetItem" not in calls
    assert 1 < calls.count("Scan") <= chunk_state._FALLBACK_SCAN_MAX_PAGES  # paginated AND bounded
    assert "DescribeTable" not in calls
