---
title: "Prerequisites"
date: 2024-01-01
weight: 2
chapter: false
pre: " <b> 5.2. </b> "
---

# 5.2. Environment Setup, AWS CLI, SAM, IAM Least-Privilege & Enabling Amazon Bedrock Model Access

---

## 1. Prerequisites & Tooling Setup

Before getting started, ensure the following developer tools are configured locally:

1. **AWS Account** with AdministratorAccess or permissions to provision IAM Roles, S3, DynamoDB, Lambda, SQS, API Gateway, and CloudWatch.
2. **AWS CLI v2**: Configured via `aws configure`.
3. **AWS SAM CLI**: Tooling for building and deploying Serverless applications.
4. **Python 3.12** & **Node.js 20+** (for running the Web UI).

### Verify AWS CLI Configuration:
```bash
aws sts get-caller-identity
aws configure get region
```
*Ensure the returned region is **`us-east-1`** (N. Virginia).*

---

## 2. Setting up Cost Guardrails (AWS Budgets)

To guarantee zero unexpected charges during development:
1. Open the **AWS Management Console** $\rightarrow$ Search for **AWS Budgets**.
2. Select **Create budget** $\rightarrow$ **Cost budget**.
3. Name: `AgentSys-Budget-5USD` $\rightarrow$ Monthly budget limit: **`$5.00 USD`**.
4. Configure an email notification trigger at `80% ($4.00 USD)`.

---

## 3. Enabling Amazon Bedrock Model Access

By default, foundation models on Amazon Bedrock require an initial access request:

1. In the **AWS Console**, navigate to **Amazon Bedrock** (Region: `us-east-1`).
2. On the left navigation pane, click **Model access** $\rightarrow$ Click **Modify model access** (or **Enable specific models**).
3. Select the required models:
   * **Amazon:** `Nova Lite`, `Titan Text Embeddings V2`, `Titan Text G1 - Lite`.
   * **Anthropic (Optional):** `Claude 3.5 Sonnet` / `Claude 3 Haiku`.
4. Click **Next** and **Submit**. The status will turn to a green **`Access granted`** badge.

{{% notice tip %}}
**Note:** Forgetting to enable model access causes `/agent/query` to return `AccessDeniedException`.
{{% /notice %}}

---

## 4. IAM Least-Privilege Architecture

The SAM template (`infra/template.yaml`) defines two strictly segregated execution roles:

1. **`IngestFunctionRole`**:
   * Scoped to `s3:GetObject` on `uploads/*`.
   * `rekognition:DetectLabels` and `rekognition:DetectText`.
   * `transcribe:StartTranscriptionJob` and `transcribe:GetTranscriptionJob`.
   * `dynamodb:PutItem` and `dynamodb:UpdateItem` on table `AgentSysMediaMetadata`.
   * Consumer access to SQS queue `agentsys-ingest-queue`.
2. **`ApiFunctionRole`**:
   * Generates `s3:PutObject` Presigned URLs.
   * `dynamodb:GetItem` and `dynamodb:Query` (including GSI `category-index`).
   * `bedrock:InvokeModel` on authorized foundation models.

---

## 5. Running Automated Unit Tests

Run the full automated test suite containing **77 test cases**:

```bash
cd agent_sys
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pytest -v
```
*Expected: All **77/77 tests passed** in ~30 seconds.*

---

## 6. Building and Deploying with AWS SAM

```bash
cd agent_sys
sam build -t infra/template.yaml
sam deploy --guided
```

### Guided Deployment Parameters:
| Parameter | Recommended Value | Purpose |
| :--- | :--- | :--- |
| **Stack Name** | `agentsys` | CloudFormation Stack Name |
| **AWS Region** | `us-east-1` | Target AWS Region |
| **Parameter ApiKey** | `your-secret-key-123` | API Protection Key (`X-API-Key` header) |
| **Confirm changes before deploy** | `Y` | Review CloudFormation changeset |
| **Allow SAM CLI IAM role creation** | `Y` | Grant SAM permission to create IAM roles |

After deployment succeeds, record the values in **Outputs**:
* `ApiEndpoint`: API Gateway Invoke URL
* `MediaBucketName`: S3 Media Bucket Name
* `MetadataTableName`: `AgentSysMediaMetadata`
