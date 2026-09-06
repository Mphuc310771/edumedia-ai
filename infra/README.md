# SAM Deployment

From the `agent_sys` directory (not `infra/`):

## Prerequisites

Before running `sam build`, ensure the `pack/` directory is prepared with all required runtime modules. The recommended approach:

```bash
python scripts/deploy_stack.py
```

This script automatically stages `apps/`, `config/`, `pipeline/`, and `requirements.txt` into `pack/` before building and deploying.

### Manual Alternative

```bash
sam build -t infra/template.yaml
sam deploy --guided --capabilities CAPABILITY_IAM
```

> **Note:** `template.yaml` uses `CodeUri: ../pack`. Lambda functions require `apps/`, `config/`, `pipeline/`, and `requirements.txt` in `pack/`. If `pack/` is missing or incomplete, the build will fail.

If the upload zip is too large, `.samignore` already excludes `gallery_web/` and `node_modules/`.

## Architecture

S3 `uploads/` notifies **SQS** (`agentsys-ingest-queue`). The ingest Lambda is an SQS consumer with a DLQ after 3 failures. The aggregator Lambda is triggered by DynamoDB Streams for transcript map-reduce processing.

## Teardown

Empty the bucket before delete:

```bash
aws s3 rm s3://<MediaBucketName> --recursive
sam delete --stack-name agentsys
```
