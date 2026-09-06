"""
Clear all media data from Amazon DynamoDB and Amazon S3 for a fresh start.
"""
from apps.aws.providers import get_runtime
from config.settings import settings
import boto3

def run():
    print("==================================================")
    print("[*] CLEARING ALL CLOUD MEDIA DATA FOR FRESH UPLOAD")
    print("==================================================")
    
    runtime = get_runtime()
    
    # 1. Clear DynamoDB Table
    print("[*] [1/2] Clearing Amazon DynamoDB Table: AgentSysMediaMetadata...")
    items = runtime.catalog.list_all()
    deleted_db_count = 0
    for item in items:
        runtime.catalog.delete(item.file_id)
        deleted_db_count += 1
    print(f"  [OK] Deleted {deleted_db_count} records from DynamoDB.")

    # 2. Clear Amazon S3 Bucket Objects
    print(f"\n[*] [2/2] Clearing Amazon S3 Bucket: {settings.MEDIA_BUCKET}...")
    from apps.aws.aws_services import _session_kwargs

    s3 = boto3.client("s3", **_session_kwargs())
    
    deleted_s3_count = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.MEDIA_BUCKET, Prefix="uploads/"):
        objects = page.get("Contents", [])
        if objects:
            delete_keys = [{"Key": obj["Key"]} for obj in objects]
            s3.delete_objects(Bucket=settings.MEDIA_BUCKET, Delete={"Objects": delete_keys})
            deleted_s3_count += len(delete_keys)
            
    print(f"  [OK] Deleted {deleted_s3_count} objects from Amazon S3.")
    print("==================================================")
    print("[SUCCESS] ALL CLOUD DATA CLEARED! READY FOR FRESH UPLOAD.")
    print("==================================================")

if __name__ == "__main__":
    run()
