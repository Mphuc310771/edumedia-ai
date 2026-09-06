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
