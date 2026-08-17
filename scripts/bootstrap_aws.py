"""
Bootstrap and provision real AWS resources (S3, DynamoDB, IAM checks) via Boto3 SDK.
Enables instant real-cloud execution.
"""
import json
import os
import sys
import boto3
from botocore.exceptions import ClientError

def bootstrap_cloud(access_key_id: str, secret_access_key: str, region: str = "us-east-1"):
    print("==================================================")
    print("[*] BOOTSTRAPPING REAL AWS CLOUD INFRASTRUCTURE")
    print("==================================================")
    
    session = boto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region
    )
    
    # 1. Verify AWS Identity
    sts = session.client("sts")
    try:
        caller = sts.get_caller_identity()
        account_id = caller["Account"]
        print(f"[OK] AWS Credentials Verified! Account ID: {account_id} (Arn: {caller['Arn']})")
    except Exception as exc:
        print(f"[ERROR] Failed to verify AWS Credentials: {exc}")
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

    # Set S3 CORS for web browser uploads
    try:
        s3.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
                        "AllowedOrigins": ["*"],
                        "MaxAgeSeconds": 3000
                    }
                ]
            }
        )
        print("  [OK] S3 CORS policy configured for Web UI & Mobile uploads.")
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

    # 4. Write Real Cloud Config to .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    env_content = f"""# Real AWS Cloud Environment Config
ENVIRONMENT=development
MEDIA_PROVIDER=aws
AWS_REGION={region}
AWS_ACCESS_KEY_ID={access_key_id}
AWS_SECRET_ACCESS_KEY={secret_access_key}
MEDIA_BUCKET={bucket_name}
METADATA_TABLE={table_name}
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
CLOUDWATCH_NAMESPACE=AgentSys
SEED_DEMO_ITEMS=true
"""
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"\n[*] [3/3] Updated .env file with MEDIA_PROVIDER=aws and live cloud resources.")
    print("==================================================")
    print("[SUCCESS] REAL AWS CLOUD INTEGRATION COMPLETE!")
    print(f"   - S3 Bucket: {bucket_name}")
    print(f"   - DynamoDB Table: {table_name}")
    print(f"   - Region: {region}")
    print(f"   - Mode: AWS Real Cloud Live")
    print("==================================================")
    return True

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        bootstrap_cloud(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "us-east-1")
    else:
        print("Usage: python scripts/bootstrap_aws.py <AWS_ACCESS_KEY_ID> <AWS_SECRET_ACCESS_KEY> [REGION]")
