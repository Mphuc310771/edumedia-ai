---
title: "Nhật ký công việc"
date: 2024-01-01
weight: 1
chapter: false
pre: " <b> 1. </b> "
---

# Nhật Ký Thực Tập 12 Tuần — FCAJ AWS Vietnam

{{% notice info %}}
📌 **Thông tin thực tập sinh:**  
- **Họ và tên:** Đỗ Trần Minh Phúc  
- **Mã sinh viên:** HCMUS - Đại học Khoa học Tự nhiên, ĐHQG-HCM  
- **Thời gian thực tập:** 12/08/2026 – 12/11/2026  
- **Đơn vị thực tập:** AWS Vietnam (Chương trình First Cloud AI Journey - Tầng 26 Bitexco, TP.HCM)  
- **Dự án thực hiện:** **AgentSys — Autonomous AI Agent for Multi-modal Media Retrieval & Management**  
{{% /notice %}}

---

### 📊 Bảng Tổng Quan Tiến Độ 12 Tuần

| Tuần | Tên Hạng Mục | Trạng Thái | Dịch Vụ AWS Liên Quan | Link Chi Tiết |
|:---:|---|:---:|---|:---:|
| **Tuần 1** | Khởi động & Nắm vững Quy định FCAJ | ✅ Complete | AWS CLI, Hugo | [Xem chi tiết](1.1-week1/) |
| **Tuần 2** | Nghiên cứu Amazon S3 & Quản lý IAM | ✅ Complete | Amazon S3, AWS IAM | [Xem chi tiết](1.2-week2/) |
| **Tuần 3** | Tìm hiểu Kiến trúc Serverless với Lambda | ✅ Complete | AWS Lambda | [Xem chi tiết](1.3-week3/) |
| **Tuần 4** | Khám phá Amazon Rekognition & Transcribe | ✅ Complete | Rekognition, Transcribe | [Xem chi tiết](1.4-week4/) |
| **Tuần 5** | Thiết kế Kiến trúc AgentSys & Viết Proposal | ✅ Complete | Draw.io, AWS Architecture | [Xem chi tiết](1.5-week5/) |
| **Tuần 6** | Khởi tạo Hạ tầng S3 & Pipeline Media | ✅ Complete | S3 Events, Lambda | [Xem chi tiết](1.6-week6/) |
| **Tuần 7** | Triển khai Tích hợp Rekognition & Transcribe | ✅ Complete | Rekognition, Transcribe, Boto3 | [Xem chi tiết](1.7-week7/) |
| **Tuần 8** | Xây dựng Database Metadata trên DynamoDB | ✅ Complete | Amazon DynamoDB | [Xem chi tiết](1.8-week8/) |
| **Tuần 9** | Tích hợp Amazon Bedrock AI Agent (Claude 3.5) | ✅ Complete | Amazon Bedrock (Claude 3.5) | [Xem chi tiết](1.9-week9/) |
| **Tuần 10** | Kiểm thử End-to-End & Giám sát CloudWatch | ✅ Complete | Amazon CloudWatch | [Xem chi tiết](1.10-week10/) |
| **Tuần 11** | Viết Bài Blog AWS & Hoàn thiện Workshop | ✅ Complete | AWS Study Group, Hugo | [Xem chi tiết](1.11-week11/) |
| **Tuần 12** | Thuyết trình Demo Day & Báo cáo Cuối kỳ | ✅ Complete | Bitexco Presentation | [Xem chi tiết](1.12-week12/) |

---

### 🚀 Chi Tiết Nội Dung Nhật Ký Theo Tuần

1. **[Tuần 1: Khởi động & Nắm vững Quy định FCAJ](1.1-week1/)**  
   *Đăng ký HCM-Portal, nắm vững quy định chuyên cần/văn phòng Tầng 26 Bitexco, cài đặt môi trường Hugo.*
2. **[Tuần 2: Nghiên cứu Amazon S3 & IAM Roles](1.2-week2/)**  
   *Thiết lập S3 Input Bucket, phân quyền IAM Least Privilege cho Lambda.*
3. **[Tuần 3: Khám phá AWS Lambda & Event-driven Architecture](1.3-week3/)**  
   *Viết Lambda Python 3.12 thử nghiệm kích hoạt bằng S3 ObjectCreated Event.*
4. **[Tuần 4: Nghiên cứu Amazon Rekognition & Transcribe](1.4-week4/)**  
   *Thử nghiệm bóc nhãn hình ảnh và chuyển giọng nói tiếng Việt thành text.*
5. **[Tuần 5: Thiết kế Kiến trúc AgentSys & Hoàn thiện Proposal](1.5-week5/)**  
   *Thiết kế sơ đồ kiến trúc hệ thống 6 dịch vụ AWS và viết bản đề xuất gửi Mentor.*
6. **[Tuần 6: Triển khai Pipeline tiếp nhận Media](1.6-week6/)**  
   *Cấu hình S3 Event Notification tự động trigger Lambda Extractor khi upload file.*
7. **[Tuần 7: Triển khai Tích hợp Rekognition & Transcribe](1.7-week7/)**  
   *Viết code Lambda trích xuất tự động metadata từ nhiều định dạng file (JPG, PNG, MP3, MP4).*
8. **[Tuần 8: Xây dựng Cơ sở Dữ liệu Metadata với DynamoDB](1.8-week8/)**  
   *Tạo bảng DynamoDB `AgentSysMediaMetadata` lưu trữ chỉ mục NoSQL.*
9. **[Tuần 9: Tích hợp Amazon Bedrock AI Agent (Claude 3.5)](1.9-week9/)**  
   *Kết nối Bedrock API, viết Prompt cho phép AI Agent hiểu câu hỏi tiếng Việt.*
10. **[Tuần 10: Kiểm thử End-to-End & Giám sát CloudWatch](1.10-week10/)**  
    *Test tải nhiều file cùng lúc, cấu hình CloudWatch Alarms theo dõi lỗi Lambda.*
11. **[Tuần 11: Viết Blog AWS & Hoàn thiện Workshop](1.11-week11/)**  
    *Soạn 3 bài blog đăng AWS Study Group và hoàn thiện 6 phần tài liệu Workshop.*
12. **[Tuần 12: Thuyết trình Demo Day & Nộp Báo cáo Cuối kỳ](1.12-week12/)**  
    *Bảo vệ thành công dự án AgentSys tại Bitexco và hoàn tất báo cáo thực tập.*
