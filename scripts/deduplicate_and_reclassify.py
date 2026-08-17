"""
Deduplicate existing items in DynamoDB and re-classify categories using the multi-signal AI classifier.
"""
from collections import defaultdict
import os
import sys

from apps.aws.providers import get_runtime
from apps.domain import infer_category

def run():
    runtime = get_runtime()
    items = runtime.catalog.list_all()
    print(f"[*] Total records found in DynamoDB: {len(items)}")

    # 1. Group by filename
    by_filename = defaultdict(list)
    for item in items:
        by_filename[item.filename].append(item)

    deleted_count = 0
    updated_count = 0

    for filename, group in by_filename.items():
        # Sort by created_at descending (keep newest)
        group.sort(key=lambda x: x.created_at, reverse=True)
        keeper = group[0]
        duplicates = group[1:]

        # Delete duplicates
        for dup in duplicates:
            runtime.catalog.delete(dup.file_id)
            deleted_count += 1

        # Re-classify category for keeper
        old_cat = keeper.category
        new_cat = infer_category(keeper.media_type, keeper.labels, f"{keeper.ocr_text} {keeper.transcript} {keeper.filename}")
        if old_cat != new_cat or duplicates:
            keeper.category = new_cat
            runtime.catalog.put(keeper)
            updated_count += 1
            safe_fn = filename.encode("ascii", "replace").decode("ascii")
            print(f"  [OK] {safe_fn} -> Category: {old_cat} => {new_cat}")

    remaining = runtime.catalog.list_all()
    print("==================================================")
    print(f"[SUCCESS] DEDUPLICATION & RE-CLASSIFICATION COMPLETE!")
    print(f"  - Deleted duplicate records: {deleted_count}")
    print(f"  - Re-classified/Updated records: {updated_count}")
    print(f"  - Clean unique items remaining: {len(remaining)}")
    print("==================================================")

if __name__ == "__main__":
    run()
