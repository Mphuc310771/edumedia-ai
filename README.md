# EduMedia AI

Smart lecture storage and semantic search platform built on AWS Serverless and Generative AI.

[![AWS SAM](https://img.shields.io/badge/AWS-SAM%20Serverless-orange?logo=amazon-aws)](https://aws.amazon.com/serverless/sam/)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev/)
[![Tests](https://img.shields.io/badge/Tests-143%20Passed-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/Coverage-84%25-brightgreen)](tests/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## Overview

EduMedia AI helps university students organize and search through lecture materials — whiteboard captures, textbook photos, audio recordings, and video clips.

Instead of manually scrolling through thousands of unorganized files in a camera roll, students can search using natural Vietnamese queries (for example: *"tìm công thức đạo hàm"* or *"bài giảng triết học phần lượng chất"*).

The platform runs completely on AWS Serverless architecture:
- Media files are stored securely in **Amazon S3** via presigned upload URLs.
- Ingestion events are buffered in **Amazon SQS** with a Dead-Letter Queue (DLQ).
- **Amazon Rekognition** handles image object detection and OCR.
- **Amazon Transcribe** generates Vietnamese (`vi-VN`) speech-to-text with timestamps.
- **Amazon Bedrock (Titan Embeddings V2 & Nova)** powers semantic query planning and 256-d vector search against metadata stored in **Amazon DynamoDB**.

---

## Architecture

![EduMedia AI Architecture](docs/agentsys-architecture.png)

### Data Pipeline Workflow:

1. **Client & Ingestion**:
   - The user requests an upload presigned URL from the FastAPI backend (running on AWS Lambda via API Gateway).
   - The browser uploads directly to S3.
   - S3 emits an `ObjectCreated` event to SQS (`agentsys-ingest-queue`).

2. **Background Processing**:
   - An ingest Lambda worker consumes messages in batches.
   - For images: calls Rekognition for label detection and text OCR.
   - For audio/video: initiates an asynchronous Transcribe job; an EventBridge rule catches job completion and writes back transcripts.
   - Extracts semantic embeddings with Amazon Titan Text Embeddings V2 (256 dimensions).
   - Writes structured metadata into DynamoDB with a Global Secondary Index (`category-index`).

3. **Stream Aggregation**:
   - DynamoDB Streams trigger an aggregator Lambda to summarize long lectures into topic-based chunks via Bedrock.

4. **Hybrid Search**:
   - User queries are parsed by Bedrock to extract intent, filters, and semantic keywords.
   - Combined scoring calculates cosine vector similarity alongside keyword overlap to return the most relevant lecture timestamps and slides.

---

## Tech Stack & AWS Services

| Service / Tool | Purpose in EduMedia AI |
| :--- | :--- |
| **Amazon S3** | Private media storage with SSE-S3 encryption and presigned upload/download URLs. |
| **Amazon SQS + DLQ** | Decoupled queue buffer between S3 and Lambda workers to prevent data loss. |
| **AWS Lambda** | Serverless compute executing FastAPI REST endpoints, ingest workers, and stream aggregators. |
| **Amazon DynamoDB** | Single-table NoSQL catalog with sub-10ms GSI queries (`category-index`) and DynamoDB Streams. |
| **Amazon Rekognition** | Object and label classification (`DetectLabels`) and text OCR extraction (`DetectText`). |
| **Amazon Transcribe** | Vietnamese speech-to-text (`vi-VN`) generating time-stamped transcripts for video/audio. |
| **Amazon Bedrock** | Query parsing with Amazon Nova and 256-d vector embeddings with Titan Text Embeddings V2. |
| **Amazon CloudWatch** | Automated alarms (error rates, DLQ message visible, throttling) and operational metrics. |
| **Amazon CloudFront** | CDN distributing the React frontend SPA with edge caching. |
| **AWS SAM** | Infrastructure as Code (IaC) declaring all AWS resources in `infra/template.yaml`. |
| **FastAPI + React 18** | REST API backend (Python 3.12) and responsive single-page frontend (Tailwind CSS, Vite). |

---

## Project Structure

```text
agent_sys/
├── apps/                    # Backend application source code
│   ├── agent/               # Query planning & search candidate retrieval
│   ├── api/                 # FastAPI routes, schemas, auth & rate limiting
│   ├── aws/                 # Boto3 AWS service integrations (S3, DynamoDB, Bedrock, etc.)
│   ├── classify/            # Taxonomy heuristics & rule-based classification
│   ├── lambda_handlers/     # AWS Lambda entry points (API proxy & SQS ingest)
│   ├── search/              # Vector cosine similarity & hybrid search engine
│   └── domain.py            # Data models and helper utilities
├── config/                  # Pydantic application settings
├── docs/                    # Architecture diagrams & specifications
├── gallery_web/             # React 18 SPA (Vite, Tailwind CSS, Lucide icons)
├── infra/                   # AWS SAM template (template.yaml)
├── pipeline/                # DynamoDB Stream aggregator & lecture chunking
├── scripts/                 # Deployment, cleanup, and benchmark scripts
├── tests/                   # Pytest test suite (143 unit & integration tests)
├── docker-compose.yml       # Local development orchestration
└── requirements.txt         # Python dependencies
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 20+ and npm
- AWS CLI configured with valid credentials (or local mock environment)

### Local Setup

**1. Backend (FastAPI):**
```bash
# Configure local environment variables
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Start API server on port 8000
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

* API Docs (Swagger): `http://localhost:8000/docs`
* Health Check: `http://localhost:8000/health`

**2. Frontend (React):**
```bash
cd gallery_web
npm install
npm run dev
```

* Web App: `http://localhost:5174`

---

## Testing

Run the test suite with coverage:

```bash
pytest tests/ -v --cov=apps --cov=pipeline --cov-fail-under=80 --cov-report=term-missing
```

All 143 tests run against local mocks (Moto and unittest mocks) without requiring live AWS credentials.

---

## Deployment (AWS SAM)

To deploy the entire serverless backend to AWS:

```bash
# Automated build & deploy (stages runtime packaging and triggers SAM)
python scripts/deploy_stack.py

# Manual SAM CLI deploy alternative
sam build -t infra/template.yaml
sam deploy --guided --capabilities CAPABILITY_IAM
```

### Resource Cleanup
To delete deployed cloud resources and prevent ongoing costs:
```bash
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh us-east-1 agentsys
```

---

## Author

- **Author:** Do Tran Minh Phuc
