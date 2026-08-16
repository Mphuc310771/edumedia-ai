# SAM

From the `agent_sys` directory (not `infra/`):

```bash
sam build -t infra/template.yaml
sam deploy --guided --capabilities CAPABILITY_IAM
```

If the upload zip is too large, `.samignore` already excludes `gallery_web/` and `node_modules/`. Lambda only needs `apps/`, `config/`, and `requirements.txt`.

S3 `uploads/` notifies **SQS** (`agentsys-ingest-queue`). The ingest Lambda is an SQS consumer with a DLQ after 3 failures.

Empty the bucket before delete:

```bash
aws s3 rm s3://<MediaBucketName> --recursive
sam delete --stack-name agentsys
```
