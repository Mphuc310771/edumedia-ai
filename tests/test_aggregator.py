import pytest

from pipeline.aggregator_lambda import (
    handler,
    process_stream_record,
    reduce_and_finalize,
    unwrap_dynamodb_image,
)
from pipeline.chunking import TranscriptChunk
from pipeline.chunk_state import (
    MemoryChunkStore,
    init_file_pipeline_state,
    mark_chunk_completed,
    save_chunks_batch,
)


def test_unwrap_dynamodb_image():
    raw = {
        "PK": {"S": "FILE#abc"},
        "chunks_completed": {"N": "3"},
        "total_chunks": {"N": "3"},
        "pipeline_status": {"S": "REFINING"},
        "is_active": {"BOOL": True},
    }
    unwrapped = unwrap_dynamodb_image(raw)
    assert unwrapped["PK"] == "FILE#abc"
    assert unwrapped["chunks_completed"] == 3
    assert unwrapped["total_chunks"] == 3
    assert unwrapped["pipeline_status"] == "REFINING"
    assert unwrapped["is_active"] is True


def test_reduce_and_finalize_strict_chronological_ordering():
    store = MemoryChunkStore()
    file_id = "lecture-order-test"

    chunks = [
        TranscriptChunk(
            chunk_id=f"{file_id}-chunk-0000",
            chunk_index=0,
            file_id=file_id,
            start_time=0.0,
            end_time=300.0,
            text="Đoạn 1",
            item_count=10,
        ),
        TranscriptChunk(
            chunk_id=f"{file_id}-chunk-0001",
            chunk_index=1,
            file_id=file_id,
            start_time=300.0,
            end_time=600.0,
            text="Đoạn 2",
            item_count=10,
        ),
        TranscriptChunk(
            chunk_id=f"{file_id}-chunk-0002",
            chunk_index=2,
            file_id=file_id,
            start_time=600.0,
            end_time=900.0,
            text="Đoạn 3",
            item_count=10,
        ),
    ]

    init_file_pipeline_state(store, file_id=file_id, total_chunks=3)
    save_chunks_batch(store, file_id=file_id, chunks=chunks)

    # Complete chunks in reverse order: 2 -> 1 -> 0
    mark_chunk_completed(store, file_id=file_id, chunk_index=2, chunk_summary="Tóm tắt phần 3 (Kết luận)")
    mark_chunk_completed(store, file_id=file_id, chunk_index=1, chunk_summary="Tóm tắt phần 2 (Thực hành)")
    mark_chunk_completed(store, file_id=file_id, chunk_index=0, chunk_summary="Tóm tắt phần 1 (Mở đầu)")

    result = reduce_and_finalize(file_id, store_or_table=store)
    assert result["pipeline_status"] == "REFINED_COMPLETED"
    assert result["chunks_count"] == 3

    # Ensure the stitched summary is ordered 1 -> 2 -> 3 (chronological, not completion order)
    expected_order = "Tóm tắt phần 1 (Mở đầu) · Tóm tắt phần 2 (Thực hành) · Tóm tắt phần 3 (Kết luận)"
    assert result["final_summary"] == expected_order

    parent = store.get_file(file_id)
    assert parent["pipeline_status"] == "REFINED_COMPLETED"
    assert parent["refined_summary"] == expected_order


def test_dynamodb_stream_event_triggers_reduce():
    store = MemoryChunkStore()
    file_id = "stream-test-file"

    init_file_pipeline_state(store, file_id=file_id, total_chunks=2)
    chunk0 = TranscriptChunk(chunk_id=f"{file_id}-chunk-0000", chunk_index=0, file_id=file_id, start_time=0.0, end_time=100.0, text="A", item_count=5)
    chunk1 = TranscriptChunk(chunk_id=f"{file_id}-chunk-0001", chunk_index=1, file_id=file_id, start_time=100.0, end_time=200.0, text="B", item_count=5)
    save_chunks_batch(store, file_id=file_id, chunks=[chunk0, chunk1])

    mark_chunk_completed(store, file_id=file_id, chunk_index=0, chunk_summary="Summary A")
    mark_chunk_completed(store, file_id=file_id, chunk_index=1, chunk_summary="Summary B")

    # Mock DynamoDB stream record for parent metadata update
    stream_record = {
        "eventName": "MODIFY",
        "dynamodb": {
            "NewImage": {
                "PK": {"S": f"FILE#{file_id}"},
                "SK": {"S": "METADATA"},
                "file_id": {"S": file_id},
                "total_chunks": {"N": "2"},
                "chunks_completed": {"N": "2"},
                "pipeline_status": {"S": "REFINING"},
            }
        },
    }

    result = process_stream_record(stream_record, store_or_table=store)
    assert result is not None
    assert result["pipeline_status"] == "REFINED_COMPLETED"
    assert result["final_summary"] == "Summary A · Summary B"


def test_stream_record_does_not_trigger_prematurely():
    store = MemoryChunkStore()
    file_id = "incomplete-file"

    init_file_pipeline_state(store, file_id=file_id, total_chunks=3)

    stream_record = {
        "eventName": "MODIFY",
        "dynamodb": {
            "NewImage": {
                "PK": {"S": f"FILE#{file_id}"},
                "SK": {"S": "METADATA"},
                "file_id": {"S": file_id},
                "total_chunks": {"N": "3"},
                "chunks_completed": {"N": "1"},  # only 1/3 completed!
                "pipeline_status": {"S": "REFINING"},
            }
        },
    }

    result = process_stream_record(stream_record, store_or_table=store)
    assert result is None


def test_reduce_and_finalize_idempotent_double_call():
    """Verify that calling reduce_and_finalize twice on the same file does not corrupt or overwrite data."""
    store = MemoryChunkStore()
    file_id = "double-call-test-file"

    init_file_pipeline_state(store, file_id=file_id, total_chunks=1)
    chunk0 = TranscriptChunk(
        chunk_id=f"{file_id}-chunk-0000",
        chunk_index=0,
        file_id=file_id,
        start_time=0.0,
        end_time=100.0,
        text="Nội dung bài giảng",
        item_count=10,
    )
    save_chunks_batch(store, file_id=file_id, chunks=[chunk0])
    mark_chunk_completed(store, file_id=file_id, chunk_index=0, chunk_summary="Tóm tắt chunk 0")

    # Call 1: First finalization
    call_1 = reduce_and_finalize(file_id, store_or_table=store)
    assert call_1["pipeline_status"] == "REFINED_COMPLETED"
    assert call_1["already_finalized"] is False
    assert call_1["final_summary"] == "Tóm tắt chunk 0"
    first_updated_at = call_1["updated_at"]

    # Call 2: Duplicate finalization (e.g. at-least-once DynamoDB stream re-delivery)
    call_2 = reduce_and_finalize(file_id, store_or_table=store)
    assert call_2["pipeline_status"] == "REFINED_COMPLETED"
    assert call_2["already_finalized"] is True
    assert call_2["final_summary"] == "Tóm tắt chunk 0"
    # Ensure original timestamp is preserved without overwrite
    assert call_2["updated_at"] == first_updated_at


def test_handler_reports_batch_item_failure_on_exception():
    """Verify that exceptions during reduce are reported in batchItemFailures with SequenceNumber rather than swallowed."""
    stream_record = {
        "eventID": "evt-err-001",
        "eventName": "MODIFY",
        "dynamodb": {
            "SequenceNumber": "100000000000000000001",
            "NewImage": {
                "PK": {"S": "FILE#corrupt-file"},
                "SK": {"S": "METADATA"},
                "file_id": {"S": "corrupt-file"},
                "total_chunks": {"N": "1"},
                "chunks_completed": {"N": "1"},
                "pipeline_status": {"S": "REFINING"},
            }
        },
    }

    # Store with missing chunks will cause reduce_and_finalize to fail
    empty_store = MemoryChunkStore()
    empty_store.files["corrupt-file"] = {"total_chunks": 1, "chunks_completed": 1}

    # Calling handler directly with failing event
    response = handler({"Records": [stream_record]}, context=None)
    # The handler processes the batch and reports the exact SequenceNumber failure
    assert response["ok"] is False
    assert "batchItemFailures" in response
    assert response["batchItemFailures"] == [{"itemIdentifier": "100000000000000000001"}]


def test_reduce_and_finalize_dynamodb_condition_expression_with_moto():
    """Verify real boto3 DynamoDB ConditionExpression syntax and ConditionalCheckFailedException handling using moto."""
    import boto3
    from moto import mock_aws

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        # Create single-table DynamoDB resource
        table = dynamodb.create_table(
            TableName="AggregatorSingleTableTest",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        file_id = "moto-dynamo-race-001"

        # 1. Insert parent metadata record
        table.put_item(
            Item={
                "PK": f"FILE#{file_id}",
                "SK": "METADATA",
                "file_id": file_id,
                "total_chunks": 2,
                "chunks_completed": 2,
                "pipeline_status": "REFINING",
            }
        )

        # 2. Insert two chunk records
        table.put_item(
            Item={
                "PK": f"FILE#{file_id}",
                "SK": "CHUNK#0000",
                "file_id": file_id,
                "chunk_index": 0,
                "summary": "Tóm tắt phần 1 từ Bedrock",
                "status": "DONE",
            }
        )
        table.put_item(
            Item={
                "PK": f"FILE#{file_id}",
                "SK": "CHUNK#0001",
                "file_id": file_id,
                "chunk_index": 1,
                "summary": "Tóm tắt phần 2 từ Bedrock",
                "status": "DONE",
            }
        )

        # 3. Call 1: First invocation on DynamoDB table -> SUT executes boto3 update_item with ConditionExpression
        res_1 = reduce_and_finalize(file_id, store_or_table=table)
        assert res_1["pipeline_status"] == "REFINED_COMPLETED"
        assert res_1["already_finalized"] is False
        assert res_1["final_summary"] == "Tóm tắt phần 1 từ Bedrock · Tóm tắt phần 2 từ Bedrock"

        # Check item in DynamoDB
        item_after_1 = table.get_item(Key={"PK": f"FILE#{file_id}", "SK": "METADATA"}).get("Item", {})
        assert item_after_1["pipeline_status"] == "REFINED_COMPLETED"
        assert item_after_1["summary"] == "Tóm tắt phần 1 từ Bedrock · Tóm tắt phần 2 từ Bedrock"
        original_updated_at = item_after_1["updated_at"]

        # 4. Call 2: Duplicate invocation -> triggers real boto3 ConditionalCheckFailedException
        res_2 = reduce_and_finalize(file_id, store_or_table=table)
        assert res_2["pipeline_status"] == "REFINED_COMPLETED"
        assert res_2["already_finalized"] is True

        # Verify DynamoDB table was NOT modified/corrupted
        item_after_2 = table.get_item(Key={"PK": f"FILE#{file_id}", "SK": "METADATA"}).get("Item", {})
        assert item_after_2["updated_at"] == original_updated_at
        assert item_after_2["summary"] == "Tóm tắt phần 1 từ Bedrock · Tóm tắt phần 2 từ Bedrock"


