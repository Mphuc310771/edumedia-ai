---
title: "Tuần 2"
date: 2024-01-01
weight: 2
chapter: false
pre: " <b> 1.2. </b> "
---

# Tuần 2: S3, IAM, khung SAM

### Công việc đã làm
- Thiết kế bucket AgentSys (Block Public Access, SSE-S3, CORS, chỉ prefix `uploads/`).
- Tách IAM ingest Lambda và API Lambda trong `infra/template.yaml`.
- Ghi rõ bước bật model Bedrock trên console (không phải IAM policy).

### Kết quả
- Template SAM và workshop 5.2–5.3 mô tả least privilege và filter S3 để output Transcribe không gọi lại ingest.
