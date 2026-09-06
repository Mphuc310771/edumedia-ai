---
title: "Self-Evaluation"
date: 2024-01-01
weight: 6
chapter: false
pre: " <b> 6. </b> "
---

# 6. Self-Evaluation

**Student:** Do Tran Minh Phuc  
**University:** VNU-HCM University of Science (HCMUS)  
**Program:** First Cloud AI Journey (FCAJ) — AWS Vietnam  
**Project:** AgentSys (Autonomous AI Agent for Multi-modal Media Cataloging & Retrieval)

---

## 1. Evaluation Against AWS 8 Competency Dimensions

| Competency Pillar | Rating | Concrete Evidence & Deliverables |
| :--- | :---: | :--- |
| **1. Technical Knowledge** | **Good** | Mastered the AWS Serverless & GenAI stack: S3, SQS Buffer, Lambda, Rekognition, Transcribe, DynamoDB, Bedrock, and CloudWatch. |
| **2. Learning Agility** | **Good** | Rapidly transitioned from monolithic designs to Cloud-Native Serverless; mastered AWS SAM Templates and FinOps principles. |
| **3. Initiative & Ownership** | **Good** | Automated 77 unit test suites, established strict IAM Least-Privilege, constructed clean resource runbooks and DLQ mechanisms. |
| **4. Discipline & Reliability** | **Good** | Strictly adhered to attendance and work protocols at the AWS 26th Floor Bitexco Office; submitted all deliverables on schedule. |
| **5. Communication & Sharing** | **Good** | Prepared full bilingual documentation (EN & VI) and published 3 deep-dive technical articles on the AWS Study Group community. |
| **6. Teamwork & Autonomy** | **Good** | Independently engineered AgentSys end-to-end (Backend, Frontend, Cloud SAM IaC) while actively consulting AWS Mentors. |
| **7. Problem Solving** | **Good** | Resolved S3-Transcribe event loops via `uploads/` vs `transcripts/` partitioning; optimized Titan vectors from 1536 to 256 dimensions. |
| **8. Deliverables & Value** | **Good** | 100% project delivery: Presigned upload $\rightarrow$ SQS $\rightarrow$ Rekognition/Transcribe $\rightarrow$ DynamoDB $\rightarrow$ Bedrock Vietnamese Query. |

---

## 2. Technical Challenges Overcome

1. **Handling Asynchronous Transcribe Latency**: Direct synchronous polling in Lambda risked 120s timeouts on large audio files. Resolved by architecting an asynchronous state machine (`INDEXING` $\rightarrow$ `READY`) backed by SQS buffering.
2. **Optimizing Vector Storage Costs**: Persisting 1536-dimensional embeddings incurred higher DynamoDB table footprints. Implemented **Titan Vector Subsampling (256-d)**, cutting storage costs by 83% while maintaining >98% accuracy.

---

## 3. Future Roadmap

* Implement automated CI/CD deployment pipelines using **AWS CodePipeline / GitHub Actions**.
* Deploy the React Web UI globally using **Amazon CloudFront + S3 Static Hosting** secured with **Amazon Cognito** user authentication.
