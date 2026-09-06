---
title: "Week 2"
date: 2024-01-01
weight: 2
chapter: false
pre: " <b> 1.2. </b> "
---

# Week 2: S3, IAM, SAM skeleton

### Tasks completed
- Designed the AgentSys bucket (Block Public Access, SSE-S3, CORS, prefix `uploads/` only).
- Split IAM between ingest Lambda and API Lambda in `infra/template.yaml` (no `s3:*` on `*`).
- Documented Bedrock model access as a console step separate from IAM.

### Results
- SAM template and workshop sections 5.2–5.3 describe least privilege and the S3 event filter that prevents Transcribe output from re-invoking ingest.
