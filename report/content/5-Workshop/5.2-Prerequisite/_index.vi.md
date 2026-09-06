---
title: "Chuẩn bị"
date: 2024-01-01
weight: 2
chapter: false
pre: " <b> 5.2. </b> "
---

# 5.2. Chuẩn Bị Môi Trường, AWS CLI, SAM, IAM Least-Privilege & Bật Amazon Bedrock Model Access

---

## 1. Yêu cầu tiên quyết & Cài đặt công cụ

Trước khi bắt đầu, bạn cần chuẩn bị các công cụ sau trên máy tính cá nhân:

1. **Tài khoản AWS (AWS Account)** có quyền quản trị viên (AdministratorAccess) hoặc quyền khởi tạo IAM Role, S3, DynamoDB, Lambda, SQS, API Gateway, CloudWatch.
2. **AWS CLI v2**: Cài đặt và cấu hình thông qua `aws configure`.
3. **AWS SAM CLI**: Công cụ đóng gói và triển khai Serverless Application Model.
4. **Python 3.12** & **Node.js 20+** (để chạy Web UI).

### Xác minh cấu hình AWS CLI:
```bash
aws sts get-caller-identity
aws configure get region
```
*Đảm bảo kết quả trả về đúng User IAM của bạn và Region là **`us-east-1`** (N. Virginia).*

---

## 2. Thiết lập Ngân sách Chống Phát sinh Chi phí (AWS Budgets)

Để đảm bảo không bao giờ vượt quá ngân sách Free Tier:
1. Mở **AWS Management Console** $\rightarrow$ Tìm dịch vụ **AWS Budgets**.
2. Chọn **Create budget** $\rightarrow$ **Cost budget**.
3. Đặt tên: `AgentSys-Budget-5USD` $\rightarrow$ Đặt hạn mức: **`$5.00 USD / tháng`**.
4. Cấu hình gửi cảnh báo Email khi chi phí thực tế đạt `80% ($4.00 USD)`.

---

## 3. Kích hoạt Quyền Truy Cập Model Trên Amazon Bedrock

Mặc định trên AWS, các mô hình Generative AI (Foundation Models) yêu cầu kích hoạt trước khi gọi API:

1. Mở **AWS Console** $\rightarrow$ Tìm dịch vụ **Amazon Bedrock** (Region: `us-east-1`).
2. Ở thanh điều hướng bên trái, chọn **Model access** $\rightarrow$ Bấm nút màu cam **Modify model access** (hoặc **Enable specific models**).
3. Đánh dấu chọn các model:
   * **Amazon:** `Nova Lite` (hoặc `Titan Text Embeddings V2`, `Titan Text G1 - Lite`).
   * **Anthropic (Tùy chọn):** `Claude 3.5 Sonnet` / `Claude 3 Haiku`.
4. Bấm **Next** và **Submit**. Trạng thái sẽ chuyển sang màu xanh lá **`Access granted`** sau vài giây.

{{% notice tip %}}
**Lưu ý:** Nếu quên kích hoạt Model Access, API tìm kiếm `/agent/query` sẽ báo lỗi `AccessDeniedException`.
{{% /notice %}}

---

## 4. Nguyên Tắc Phân Quyền Tối Thiểu (IAM Least-Privilege Roles)

Trong file SAM Template (`infra/template.yaml`), hệ thống tự động khởi tạo 2 Execution Role độc lập:

1. **`IngestFunctionRole`**:
   * Chỉ có quyền `s3:GetObject` trên bucket `uploads/*`.
   * Quyền `rekognition:DetectLabels` và `rekognition:DetectText`.
   * Quyền `transcribe:StartTranscriptionJob` và `transcribe:GetTranscriptionJob`.
   * Quyền `dynamodb:PutItem`, `dynamodb:UpdateItem` trên bảng `AgentSysMediaMetadata`.
   * Quyền tiêu thụ tin nhắn từ `agentsys-ingest-queue`.
2. **`ApiFunctionRole`**:
   * Quyền tạo `s3:PutObject` Presigned URL.
   * Quyền đọc `dynamodb:GetItem`, `dynamodb:Query` (bao gồm GSI `category-index`).
   * Quyền `bedrock:InvokeModel` trên các foundation models được cấp phép.

---

## 5. Chạy Kiểm Thử Tự Động Trước Khi Triển Khai (Unit Testing)

Chạy bộ kiểm thử toàn diện gồm **77 test cases** để đảm bảo logic hoàn hảo:

```bash
cd agent_sys
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pytest -v
```
*Kỳ vọng: Toàn bộ **77/77 tests passed** trong ~30 giây.*

---

## 6. Đóng Gói & Triển Khai Bằng AWS SAM (Build & Deploy)

```bash
cd agent_sys
sam build -t infra/template.yaml
sam deploy --guided
```

### Các thông số nhập trong SAM Guided Deploy:
| Tham số | Giá trị đề xuất | Ý nghĩa |
| :--- | :--- | :--- |
| **Stack Name** | `agentsys` | Tên CloudFormation Stack |
| **AWS Region** | `us-east-1` | Khu vực triển khai hỗ trợ đầy đủ Bedrock |
| **Parameter ApiKey** | `your-secret-key-123` | Khóa bảo vệ API (Header `X-API-Key`) |
| **Confirm changes before deploy** | `Y` | Xác nhận tài nguyên trước khi tạo |
| **Allow SAM CLI IAM role creation** | `Y` | Cho phép SAM tự động tạo IAM Roles |

Sau khi triển khai hoàn tất, lưu lại các giá trị trong bảng **Outputs**:
* `ApiEndpoint`: URL gọi API Gateway (ví dụ: `https://xxxx.execute-api.us-east-1.amazonaws.com/Prod`)
* `MediaBucketName`: Tên S3 Bucket lưu trữ media
* `MetadataTableName`: `AgentSysMediaMetadata`
