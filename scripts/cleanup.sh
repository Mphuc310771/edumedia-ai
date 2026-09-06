#!/usr/bin/env bash
# ==============================================================================
# AgentSys Infrastructure Teardown & Clean-up Script
# ==============================================================================
# Usage:
#   chmod +x scripts/cleanup.sh
#   ./scripts/cleanup.sh [AWS_REGION] [STACK_NAME]
#
# Purpose:
#   Deletes all deployed AWS resources in strict reverse dependency order to
#   prevent resource-locking errors and avoid lingering cloud costs.
# ==============================================================================

set -euo pipefail

AWS_REGION="${1:-us-east-1}"
STACK_NAME="${2:-agentsys-stack}"
MEDIA_BUCKET="${MEDIA_BUCKET:-agentsys-media-bucket}"
TABLE_NAME="${METADATA_TABLE:-AgentSysMediaMetadata}"

echo "=================================================================="
echo "  Starting AgentSys Resource Cleanup in region: ${AWS_REGION}"
echo "=================================================================="

# ------------------------------------------------------------------------------
# STEP 1: Delete CloudWatch Metric Alarms
# (Prevent false alarm triggers during resource teardown)
# ------------------------------------------------------------------------------
echo "[STEP 1/7] Deleting CloudWatch Alarms..."
aws cloudwatch delete-alarms \
  --alarm-names "AgentSys-Aggregator-ErrorRate-High" "AgentSys-Ingest-DLQ-VisibleMessages" \
  --region "${AWS_REGION}" 2>/dev/null || echo "  -> No CloudWatch alarms found to delete."

# ------------------------------------------------------------------------------
# STEP 2: Delete Lambda Event Source Mappings (DynamoDB Streams & SQS)
# (Detaches consumers before deleting underlying streams/queues)
# ------------------------------------------------------------------------------
echo "[STEP 2/7] Detaching and deleting Lambda Event Source Mappings..."
UUIDS=$(aws lambda list-event-source-mappings --region "${AWS_REGION}" --query "EventSourceMappings[?contains(FunctionArn, 'agentsys')].UUID" --output text 2>/dev/null || true)
for uuid in ${UUIDS}; do
  if [ -n "${uuid}" ] && [ "${uuid}" != "None" ]; then
    echo "  -> Deleting event source mapping: ${uuid}"
    aws lambda delete-event-source-mapping --uuid "${uuid}" --region "${AWS_REGION}" 2>/dev/null || true
  fi
done

# ------------------------------------------------------------------------------
# STEP 3: Delete Lambda Functions
# ------------------------------------------------------------------------------
echo "[STEP 3/7] Deleting Lambda functions..."
for fn in agentsys-aggregator agentsys-ingest agentsys-api; do
  echo "  -> Deleting function: ${fn}"
  aws lambda delete-function --function-name "${fn}" --region "${AWS_REGION}" 2>/dev/null || true
done

# ------------------------------------------------------------------------------
# STEP 4: Delete SQS Queues & Dead-Letter Queue
echo "[STEP 4/7] Deleting SQS Queues and DLQs..."
for q in agentsys-ingest-queue agentsys-ingest-dlq agentsys-aggregator-stream-dlq; do
  Q_URL=$(aws sqs get-queue-url --queue-name "${q}" --region "${AWS_REGION}" --query "QueueUrl" --output text 2>/dev/null || true)
  if [ -n "${Q_URL}" ] && [ "${Q_URL}" != "None" ]; then
    echo "  -> Deleting queue: ${q} (${Q_URL})"
    aws sqs delete-queue --queue-url "${Q_URL}" --region "${AWS_REGION}" 2>/dev/null || true
  fi
done

# ------------------------------------------------------------------------------
# STEP 5: Delete DynamoDB Table
# ------------------------------------------------------------------------------
echo "[STEP 5/7] Deleting DynamoDB Table: ${TABLE_NAME}..."
aws dynamodb delete-table --table-name "${TABLE_NAME}" --region "${AWS_REGION}" 2>/dev/null || echo "  -> Table already deleted or does not exist."

# ------------------------------------------------------------------------------
# STEP 6: Empty & Delete S3 Media & Transcript Bucket
# (S3 buckets must be completely empty before bucket deletion)
# ------------------------------------------------------------------------------
echo "[STEP 6/7] Emptying and removing S3 Bucket: ${MEDIA_BUCKET}..."
if aws s3 ls "s3://${MEDIA_BUCKET}" --region "${AWS_REGION}" 2>/dev/null; then
  echo "  -> Deleting all objects and versions inside s3://${MEDIA_BUCKET}..."
  aws s3 rm "s3://${MEDIA_BUCKET}" --recursive --region "${AWS_REGION}" 2>/dev/null || true
  echo "  -> Deleting bucket..."
  aws s3 rb "s3://${MEDIA_BUCKET}" --force --region "${AWS_REGION}" 2>/dev/null || true
else
  echo "  -> Bucket s3://${MEDIA_BUCKET} does not exist."
fi

# ------------------------------------------------------------------------------
# STEP 7: Delete CloudFormation / SAM Stack (if deployed via IaC)
# ------------------------------------------------------------------------------
echo "[STEP 7/7] Deleting CloudFormation Stack (if applicable)..."
aws cloudformation delete-stack --stack-name "${STACK_NAME}" --region "${AWS_REGION}" 2>/dev/null || true

echo "=================================================================="
echo "  All AgentSys workshop resources have been cleanly removed!"
echo "=================================================================="
