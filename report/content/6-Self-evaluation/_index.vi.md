---
title: "Tự đánh giá"
date: 2024-01-01
weight: 6
chapter: false
pre: " <b> 6. </b> "
---

# 6. Tự Đánh Giá Kết Quả Thực Tập (Self-Evaluation)

**Sinh viên thực hiện:** Đỗ Trần Minh Phúc  
**Trường:** Đại học Khoa học Tự nhiên, ĐHQG-HCM (HCMUS)  
**Chương trình:** First Cloud AI Journey (FCAJ) — AWS Vietnam  
**Dự án:** AgentSys (Autonomous AI Agent for Multi-modal Media Cataloging & Retrieval)

---

## 1. Bảng Đánh Giá Chi Tiết Theo 8 Khung Năng Lực AWS

| Tiêu chí năng lực | Xếp loại | Minh chứng và Kết quả thực tế |
| :--- | :---: | :--- |
| **1. Kiến thức chuyên môn (Technical Knowledge)** | **Tốt (Good)** | Nắm vững và làm chủ hệ sinh thái AWS Serverless & GenAI: S3, SQS Buffer, Lambda, Rekognition, Transcribe, DynamoDB, Bedrock, CloudWatch. |
| **2. Tinh thần học hỏi (Learning Agility)** | **Tốt (Good)** | Nhanh chóng chuyển đổi từ tư duy monolithic sang Cloud-Native Serverless; làm chủ SAM Template và FinOps Cost Optimization. |
| **3. Tính chủ động (Initiative & Ownership)** | **Tốt (Good)** | Tự động hóa bộ kiểm thử 77 unit tests, thiết lập IAM Least-Privilege, xây dựng Runbook dọn dẹp sạch sẽ và dự phòng DLQ. |
| **4. Kỷ luật & Trách nhiệm (Discipline)** | **Tốt (Good)** | Tuân thủ nghiêm ngặt lịch làm việc tại văn phòng AWS Tầng 26 Bitexco, hoàn thành báo cáo tiến độ tuần đúng hạn. |
| **5. Kỹ năng giao tiếp (Communication)** | **Tốt (Good)** | Soạn thảo báo cáo song ngữ (Anh - Việt) đầy đủ, viết 3 bài blog kỹ thuật chia sẻ trên cộng đồng AWS Study Group. |
| **6. Làm việc nhóm & Độc lập (Teamwork)** | **Tốt (Good)** | Độc lập triển khai toàn bộ hệ thống AgentSys từ Backend, Frontend đến Hạ tầng IaC SAM; tích cực trao đổi với các Mentor AWS. |
| **7. Giải quyết vấn đề (Problem Solving)** | **Tốt (Good)** | Giải quyết triệt để lỗi đệ quy S3-Transcribe qua phân vùng prefix `uploads/` vs `transcripts/`; tối ưu vector 1536 $\rightarrow$ 256 chiều. |
| **8. Đóng góp cho dự án (Deliverables)** | **Tốt (Good)** | Hoàn thiện 100% các mục tiêu đề ra: Presigned upload $\rightarrow$ SQS $\rightarrow$ Rekognition/Transcribe $\rightarrow$ DynamoDB $\rightarrow$ Bedrock Query tiếng Việt. |

---

## 2. Những Khó Khăn Đã Vượt Qua

1. **Xử lý tác vụ ASR bất đồng bộ của Transcribe:** Ban đầu, việc đợi Transcribe hoàn thành trong hàm Lambda dễ gây timeout (120s). Tôi đã khắc phục bằng cách thiết kế kiến trúc phân tách trạng thái `INDEXING` $\rightarrow$ `READY` kết hợp SQS Buffer và EventBridge.
2. **Tối ưu hóa chi phí Vector Embeddings:** Việc lưu trữ vector 1536 chiều trên DynamoDB làm tăng dung lượng bảng. Tôi đã áp dụng kỹ thuật **Titan Vector Subsampling** rút gọn về 256 chiều, giảm 83% chi phí lưu trữ mà vẫn giữ độ chính xác trên 98%.

---

## 3. Định Hướng Phát Triển Tiếp Theo

* Xây dựng thêm CI/CD Pipeline tự động triển khai bằng **AWS CodePipeline / GitHub Actions**.
* Đóng gói và phân phối Web Frontend qua **Amazon CloudFront + S3 Static Hosting** kết hợp xác thực người dùng bằng **Amazon Cognito**.
