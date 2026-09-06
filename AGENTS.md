# AgentSys Project Guide

## 1. Mục tiêu dự án
AgentSys là hệ thống tìm kiếm catalog đa phương tiện (ảnh, audio, video) Serverless trên AWS:
- S3 (lưu file) -> SQS + DLQ -> Lambda (Rekognition/Transcribe) -> DynamoDB.
- Tìm kiếm: Bedrock (Nova Lite/Claude) xử lý câu hỏi tiếng Việt -> Hybrid search DynamoDB.

## 2. Quy tắc cho AI:
- KHÔNG tự ý tạo thêm thư mục mới ngoài cấu trúc: `apps/`, `infra/`, `tests/`.
- KHÔNG chỉnh sửa hoặc quét vào `.aws-sam/` hay `gallery_web/node_modules/`.
- Code backend nằm ở: `apps/aws/aws_services.py` và `apps/agent/search.py`.
- Mọi thay đổi phải tuân thủ Serverless (IaC dùng SAM template).
