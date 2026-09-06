---
title: "Week 6"
date: 2024-01-01
weight: 6
chapter: false
pre: " <b> 1.6. </b> "
---

# Week 6: Triển khai S3 Bucket & Pipeline tiếp nhận Media

### Tasks Completed:
- Cấu hình S3 Event Notification kích hoạt Lambda Extractor khi upload file
- Debugged S3-to-SQS event notification JSON wrapping (double-encoded body).
- Implemented Dead-Letter Queue with maxReceiveCount=3 for failed ingest messages.

### Results Achieved:
- Hệ thống tự động phát hiện file đa phương tiện tải lên
