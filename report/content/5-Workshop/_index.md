---
title: "Workshop"
date: 2024-01-01
weight: 5
chapter: false
pre: " <b> 5. </b> "
---

# AgentSys: Multi-modal Media Retrieval & Cataloging System on AWS

This hands-on workshop guides you step-by-step through architecting and deploying **AgentSys** using the **AWS Serverless Application Model (AWS SAM)**.

Upon completing this workshop, you will operate an end-to-end cloud-native system:
* Secure media uploads (images, audio, video) to **Amazon S3** via **Presigned URLs**.
* Asynchronous ingestion buffering with **Amazon SQS & Dead-Letter Queue (DLQ)** triggering **AWS Lambda**.
* Automated computer vision object detection & Vietnamese OCR via **Amazon Rekognition**; Vietnamese speech-to-text (*vi-VN*) via **Amazon Transcribe**.
* Vector embeddings using **Amazon Bedrock (Amazon Titan Text Embeddings V2)** and persistence in **Amazon DynamoDB**.
* Conversational Vietnamese semantic retrieval powered by **Amazon Bedrock (Nova Lite)**.
* Automated observability with **Amazon CloudWatch Logs & Alarms**.

---

### 📚 Hands-on Lab Modules:

1. **[5.1. Problem Overview, Serverless Architecture & FinOps Estimation](5.1-Workshop-overview/)**
2. **[5.2. Environment Setup, AWS CLI, SAM, IAM Least-Privilege & Bedrock Model Access](5.2-Prerequisite/)**
3. **[5.3. Configuring Amazon S3, SQS Buffer Queue, Dead-Letter Queue (DLQ) & Event Notifications](5.3-S3-Storage/)**
4. **[5.4. Deploying Lambda Ingestion Engine with Amazon Rekognition & Transcribe vi-VN](5.4-AI-Pipeline/)**
5. **[5.5. Building Search Agent with Amazon Bedrock & DynamoDB GSI Catalog](5.5-Bedrock-Search/)**
6. **[5.6. Setting up CloudWatch Monitoring, Alarms and Resource Cleanup Runbook](5.6-Monitoring-Cleanup/)**

---

* **Estimated Time:** 90 – 120 minutes.
* **Target AWS Region:** `us-east-1` (N. Virginia).
* **Estimated Lab Cost:** **`$0.00 USD`** (100% within AWS Free Tier) or `< $0.10 USD` if limits exceeded.
* **Attached Assets:** [Official SAM Template (template.yaml)](/files/agentsys-sam-template.yaml) · [Architecture Diagram (Draw.io XML)](/files/agentsys-architecture.drawio)
