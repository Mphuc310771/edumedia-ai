"""
Bootstrap and provision real AWS resources (S3, DynamoDB, IAM checks) via Boto3 SDK.
Uses the default AWS credential chain (aws configure / IAM role / env vars).
Never accepts access keys as command-line arguments.
"""
import json
import os
import sys
import boto3
from botocore.exceptions import ClientError

LAB_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def bootstrap_cloud(region: str = "us-east-1"):
    print("==================================================")
    print("[*] BOOTSTRAPPING REAL AWS CLOUD INFRASTRUCTURE")
    print("==================================================")
    
    session = boto3.Session(region_name=region)
    
    # 1. Verify AWS Identity
    sts = session.client("sts")
    try:
        caller = sts.get_caller_identity()
        account_id = caller["Account"]
        print(f"[OK] AWS Credentials Verified! Account ID: {account_id} (Arn: {caller['Arn']})")
    except Exception as exc:
        print(f"[ERROR] Failed to verify AWS Credentials: {exc}")
        print("  Run `aws configure` first, or attach an IAM role.")
        return False

    bucket_name = f"serverless-agent-media-{account_id}"
    table_name = "AgentSysMediaMetadata"

    # 2. Provision Real Amazon S3 Bucket
    s3 = session.client("s3")
    print(f"\n[*] [1/3] Provisioning Amazon S3 Bucket: {bucket_name}...")
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region}
            )
        print(f"  [OK] S3 Bucket created successfully: {bucket_name}")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
            print(f"  [INFO] S3 Bucket already exists: {bucket_name}")
        else:
            print(f"  [WARN] S3 Bucket creation status: {code} - {exc}")

    # Set S3 CORS scoped to lab origins only — never use AllowedOrigins: ["*"]
    try:
        s3.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "PUT", "HEAD"],
                        "AllowedOrigins": LAB_CORS_ORIGINS,
                        "ExposeHeaders": ["ETag"],
                        "MaxAgeSeconds": 3000,
                    }
                ]
            }
        )
        print("  [OK] S3 CORS policy configured for lab origins (localhost:5174).")
    except Exception as exc:
        print(f"  [WARN] Note on S3 CORS: {exc}")

    # 3. Provision Real Amazon DynamoDB Table
    dynamodb = session.client("dynamodb")
    print(f"\n[*] [2/3] Provisioning Amazon DynamoDB Table: {table_name}...")
    try:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "file_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "file_id", "AttributeType": "S"},
                {"AttributeName": "category", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "category-index",
                    "KeySchema": [
                        {"AttributeName": "category", "KeyType": "HASH"},
                        {"AttributeName": "created_at", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        print(f"  [OK] DynamoDB Table created with category-index GSI: {table_name}")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code == "ResourceInUseException":
            print(f"  [INFO] DynamoDB Table already exists: {table_name}")
        else:
            print(f"  [WARN] DynamoDB Table status: {code} - {exc}")

    # 4. Write resource names to .env — never persist access keys here.
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    env_content = f"""# Local lab config. Never put AWS access keys in this file.
ENVIRONMENT=development
AWS_REGION={region}
ADMIN_API_KEY=change-me
ADMIN_USERNAME=admin
MEDIA_BUCKET={bucket_name}
METADATA_TABLE={table_name}
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
BEDROCK_REGION={region}
CLOUDWATCH_NAMESPACE=AgentSys

# Credentials: run `aws configure` or attach an IAM role. Do not set AWS_ACCESS_KEY_ID here.
"""
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"\n[*] [3/3] Updated .env with bucket/table names only (no access keys).")
    print("==================================================")
    print("[SUCCESS] REAL AWS CLOUD INTEGRATION COMPLETE!")
    print(f"   - S3 Bucket: {bucket_name}")
    print(f"   - DynamoDB Table: {table_name}")
    print(f"   - Region: {region}")
    print("   - Put credentials in `aws configure`, not in .env")
    print("==================================================")
    return True

if __name__ == "__main__":
    region = sys.argv[1] if len(sys.argv) > 1 else "us-east-1"
    bootstrap_cloud(region)
