# Serverless Multi-Modal Agent

[![AWS SAM](https://img.shields.io/badge/AWS-SAM%20Serverless-orange?logo=amazon-aws)](https://aws.amazon.com/serverless/sam/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev/)
[![Tests](https://img.shields.io/badge/Tests-25%20Passed-brightgreen)](tests/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> **Event-driven multimodal media intelligence and semantic retrieval platform built on AWS Serverless, Amazon Bedrock Generative AI, and Vector Embeddings.**

---

## 🏛️ Architecture Overview

```mermaid
flowchart TD
    Client([📱 Client Web / Mobile]):::client -->|Presigned PUT / REST API| S3[(Amazon S3 Private Media Bucket)]:::aws
    Client <-->|REST API / Cognito Auth| APIGW[Amazon API Gateway HTTP API]:::aws
    APIGW <--> LambdaAPI[AWS Lambda FastAPI API]:::aws
    
    S3 -->|s3:ObjectCreated Notification| SQS[Amazon SQS Ingest Queue]:::aws
    SQS -->|Failed 3x| DLQ[Amazon SQS Dead-Letter Queue]:::aws
    SQS --> LambdaWorker[AWS Lambda Ingest Worker]:::aws
    
    LambdaWorker -->|Image| Rekognition[Amazon Rekognition: DetectLabels + OCR Text]:::ai
    LambdaWorker -->|Audio / Video Async| Transcribe[Amazon Transcribe: vi-VN Speech-to-Text]:::ai
    
    Transcribe -.->|Job State Change Event| EventBridge[Amazon EventBridge Rule]:::aws
    EventBridge -.->|Trigger Completion Callback| LambdaWorker
    
    Rekognition --> DynamoDB[(Amazon DynamoDB GSI category-index)]:::aws
    Transcribe --> DynamoDB
    
    LambdaAPI <-->|Titan Multimodal Embeddings & Cosine Search| TitanEmbed[Amazon Titan Vector Embeddings]:::ai
    LambdaAPI <-->|Query Planning: Nova Lite / Claude 3.5| Bedrock[Amazon Bedrock Agent]:::ai
    LambdaAPI <--> DynamoDB
    
    LambdaWorker --> CloudWatch[Amazon CloudWatch Metrics & Alarms]:::aws

    classDef aws fill:#232F3E,stroke:#FF9900,stroke-width:2px,color:#fff;
    classDef ai fill:#0D5265,stroke:#00A4A6,stroke-width:2px,color:#fff;
    classDef client fill:#10B981,stroke:#059669,stroke-width:2px,color:#fff;
```

---

## ☁️ Integrated AWS Services

| Service | Architecture Role |
| :--- | :--- |
| **Amazon S3** | Encrypted private media storage with SSE-S3, Presigned URLs, and ObjectCreated event triggers. |
| **Amazon SQS + DLQ** | Decoupled event-driven buffer with Dead-Letter Queue isolation after 3 failed retries. |
| **AWS Lambda** | Serverless compute executing FastAPI REST endpoints (`ApiFunction`) and background worker (`IngestWorkerFunction`). |
| **Amazon Rekognition** | Computer vision label classification (`DetectLabels`) and OCR text extraction (`DetectText`). |
| **Amazon Transcribe** | Speech-to-text pipeline transcribing Vietnamese audio lectures (`vi-VN`) into indexed text. |
| **Amazon Bedrock** | Generative AI query planning (Nova Lite / Claude 3.5 Sonnet) translating natural queries into structured search plans. |
| **Amazon DynamoDB** | On-demand NoSQL document store with sub-10ms GSI queries (`category-index`). |
| **Amazon CloudWatch** | End-to-end observability: Custom metric telemetry (`MediaIngested`), structured logs, and automated alarms. |
| **AWS IAM** | Granular least-privilege role policies scoped per Lambda function (no static credentials). |
| **AWS SAM** | Infrastructure as Code (IaC) automating multi-service cloud provisioning via declarative templates. |

---

## 🚀 Quickstart & Local Testing

### 1. Launch Everything (1-Click on Windows):
Double-click `start_app.bat` to launch the FastAPI backend, React frontend, and open your browser automatically.

### 2. Manual Start:

**Backend API:**
```bash
pip install -r requirements.txt
python -m uvicorn apps.api.main:app --port 8000 --reload
```

**Frontend UI:**
```bash
cd gallery_web
npm install
npm run dev
```

* **Web Application:** `http://localhost:5174` (or mobile on LAN: `http://<LAN_IP>:5174`)
* **API Documentation:** `http://localhost:8000/docs`
* **Health Endpoint:** `http://localhost:8000/health`

---

## 🧪 Automated Testing & Verification

Run the full test suite (21 unit tests, ingest event simulation, search resilience, and SAM template validation):

```bash
pytest tests/ -v
```

Pre-flight compliance check:
```bash
python scripts/verify_local.py
```

---

## 🚢 Cloud Deployment (AWS SAM)

```bash
# 1. Build serverless artifacts
sam build -t infra/template.yaml

# 2. Deploy to AWS
sam deploy --guided --capabilities CAPABILITY_IAM
```

Tear down resources after evaluation:
```bash
sam delete --stack-name agentsys
```

---

## 👨‍💻 Author & Program
* **Author:** Đỗ Trần Minh Phúc (HCMUS)
* **Program:** First Cloud AI Journey (FCAJ) — AWS Vietnam
