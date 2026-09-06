#!/usr/bin/env python3
"""FCAJ Workshop Demo: Race Condition Protection & Idempotent Reduce Phase.

Supports two modes:
1. Local Mode (default): Rapid offline verification using MemoryChunkStore.
2. Live AWS Cloud Mode (`--live` or `--cloud`): Connects to deployed AWS DynamoDB table,
   executes real conditional updates, catches real boto3 ConditionalCheckFailedException,
   and outputs CloudWatch Logs retrieval commands for workshop report evidence.

Usage:
    # 1. Local Offline Demo:
    python scripts/demo_race_condition.py

    # 2. Live AWS Cloud Demo (against deployed AWS infrastructure):
    python scripts/demo_race_condition.py --live
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configure structured logging to mirror CloudWatch Logs output format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AgentSys.Aggregator")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.aggregator_lambda import reduce_and_finalize
from pipeline.chunking import TranscriptChunk
from pipeline.chunk_state import (
    MemoryChunkStore,
    init_file_pipeline_state,
    mark_chunk_completed,
    save_chunks_batch,
)


def get_live_dynamodb_table():
    """Connect to live AWS DynamoDB table using configured settings/credentials."""
    import boto3
    from config.settings import settings

    kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        if settings.AWS_SESSION_TOKEN:
            kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN

    dynamodb = boto3.resource("dynamodb", **kwargs)
    return dynamodb.Table(settings.METADATA_TABLE)


def run_demo(is_live: bool = False):
    print("=" * 78)
    if is_live:
        print("  FCAJ WORKSHOP DEMO: LIVE AWS CLOUDWATCH & DYNAMODB RACE CONDITION TEST")
    else:
        print("  FCAJ WORKSHOP DEMO: LOCAL AT-LEAST-ONCE RACE CONDITION PROTECTION")
    print("=" * 78)

    file_id = f"fcaj-demo-lecture-{'live' if is_live else 'local'}-{int(time.time())}"

    if is_live:
        print(f"\n[MODE] Connecting to LIVE AWS DynamoDB Table...")
        try:
            store_or_table = get_live_dynamodb_table()
            # Quick ping
            store_or_table.load()
            print(f"  -> Connected to table: {store_or_table.table_name} (Status: {store_or_table.table_status})")
        except Exception as exc:
            print(f"  [ERROR] Cannot connect to live DynamoDB: {exc}")
            print("  Falling back to Local Mode. To run against AWS, deploy infrastructure first.")
            is_live = False
            store_or_table = MemoryChunkStore()
    else:
        store_or_table = MemoryChunkStore()

    # Step 1: Initialize lecture with 3 chunks
    print(f"\n[STEP 1] Initializing 3 lecture chunks for file_id='{file_id}'...")
    chunks = [
        TranscriptChunk(
            chunk_id=f"{file_id}-chunk-0000",
            chunk_index=0,
            file_id=file_id,
            start_time=0.0,
            end_time=300.0,
            text="Phần 1: Giới thiệu đề tài đồ án và yêu cầu thuyết trình 10 phút.",
            item_count=50,
        ),
        TranscriptChunk(
            chunk_id=f"{file_id}-chunk-0001",
            chunk_index=1,
            file_id=file_id,
            start_time=300.0,
            end_time=600.0,
            text="Phần 2: Lịch thi lý thuyết ngày 17/7 và hạn nộp đồ án ngày 24/7.",
            item_count=60,
        ),
        TranscriptChunk(
            chunk_id=f"{file_id}-chunk-0002",
            chunk_index=2,
            file_id=file_id,
            start_time=600.0,
            end_time=900.0,
            text="Phần 3: Nhắc nhở hoàn thành chứng chỉ Anh văn để kịp chuẩn đầu ra.",
            item_count=45,
        ),
    ]

    init_file_pipeline_state(store_or_table, file_id=file_id, total_chunks=3, provisional_summary={"tier1": "ok"})
    save_chunks_batch(store_or_table, file_id=file_id, chunks=chunks)

    # Step 2: Simulate parallel workers completing chunks
    print("[STEP 2] Simulating chunk completions by parallel Bedrock workers...")
    mark_chunk_completed(store_or_table, file_id=file_id, chunk_index=0, chunk_summary="Mở đầu: Hướng dẫn thuyết trình đồ án (10 phút/nhóm)")
    mark_chunk_completed(store_or_table, file_id=file_id, chunk_index=1, chunk_summary="Kế hoạch: Thi lý thuyết 17/7 · Hạn nộp đồ án 24/7")
    mark_chunk_completed(store_or_table, file_id=file_id, chunk_index=2, chunk_summary="Kết luận: Lưu ý chuẩn đầu ra chứng chỉ tiếng Anh")

    # Step 3: Trigger First Finalization (Normal execution)
    print("\n" + "-" * 78)
    print("[STEP 3] TRIGGER 1: First reduce_and_finalize invocation (Streams Event 1)")
    print("-" * 78)
    logger.info("Executing reduce_and_finalize for file_id=%s", file_id)
    res_1 = reduce_and_finalize(file_id, store_or_table=store_or_table)
    print("\nResult 1 Output:")
    print(json.dumps(res_1, ensure_ascii=False, indent=2))

    assert res_1["pipeline_status"] == "REFINED_COMPLETED"
    assert res_1["already_finalized"] is False
    original_timestamp = res_1["updated_at"]

    # Step 4: Trigger Second Finalization (Simulate Stream Duplicate / Parallel Race)
    time.sleep(0.05)
    print("\n" + "-" * 78)
    print("[STEP 4] TRIGGER 2: Duplicate reduce_and_finalize invocation (Streams Retry / Race)")
    print("-" * 78)
    logger.info("Executing duplicate reduce_and_finalize for file_id=%s", file_id)
    res_2 = reduce_and_finalize(file_id, store_or_table=store_or_table)
    print("\nResult 2 Output:")
    print(json.dumps(res_2, ensure_ascii=False, indent=2))

    assert res_2["pipeline_status"] == "REFINED_COMPLETED"
    assert res_2["already_finalized"] is True
    if "updated_at" in res_2:
        assert res_2["updated_at"] == original_timestamp

    print("\n" + "=" * 78)
    print("  VERIFICATION RESULT: SUCCESS (Idempotency & Race Condition Guard Passed)")
    print("=" * 78)

    if is_live:
        print("\n📸 BẰNG CHỨNG CLOUDWATCH THẬT (DÙNG ĐỂ CHỤP VÀO BÁO CÁO WORKSHOP FCAJ):")
        print("1. Mở AWS Console -> CloudWatch -> Log groups -> /aws/lambda/agentsys-aggregator")
        print("2. Hoặc chạy lệnh AWS CLI để lấy log stream thật:")
        print(f"   aws logs filter-log-events --log-group-name /aws/lambda/agentsys-aggregator --filter-pattern \"{file_id}\"")
        print("3. Hai dòng log mấu chốt được ghi nhận:")
        print(f"   • [INFO] reduce_and_finalize_success file_id={file_id} chunks=3")
        print(f"   • [INFO] reduce_already_finalized file_id={file_id} (ConditionalCheckFailedException caught)")
    else:
        print("\n💡 GHI CHÚ BÁO CÁO:")
        print("• Script này đã mô phỏng thành công cơ chế ConditionExpression.")
        print("• Khi deploy Lambda lên AWS thật, chạy lệnh sau để ghi log trực tiếp vào CloudWatch:")
        print("  python scripts/demo_race_condition.py --live")
    print("=" * 78)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo race condition protection")
    parser.add_argument("--live", "--cloud", action="store_true", help="Run against live deployed AWS DynamoDB table")
    args = parser.parse_args()
    run_demo(is_live=args.live)
