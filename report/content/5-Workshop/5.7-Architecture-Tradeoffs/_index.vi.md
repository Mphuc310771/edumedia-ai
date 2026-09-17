---
title: "Kiến trúc đánh đổi & Hướng phát triển"
date: 2024-01-01
weight: 7
chapter: false
pre: " <b> 5.7. </b> "
---

# 5.7. Thảo luận: Kiến trúc Đánh đổi & Lộ trình Nâng cấp Enterprise (Architecture Trade-offs & Enterprise Roadmap)

Trong giai đoạn xây dựng PoC (Proof of Concept) phục vụ chương trình First Cloud AI Journey (FCAJ), mục tiêu cốt lõi của AgentSys là hiện thực hóa một hệ thống tìm kiếm đa phương tiện thông minh bằng AI, tuân thủ kiến trúc Serverless với tiêu chí **tối ưu chi phí tối đa (Zero-Idle-Cost)** và **triển khai tinh gọn (Lean Architecture)**. 

Để đạt được sự cân bằng giữa chi phí học tập/thực nghiệm và tính năng, một số quyết định đánh đổi kiến trúc (architectural trade-offs) có chủ đích đã được áp dụng. Dưới đây là phân tích phản biện kỹ thuật về 4 giới hạn hiện tại của hệ thống và giải pháp mở rộng chuẩn AWS Enterprise khi đưa vào môi trường sản xuất quy mô lớn.

---

### 1. Giới hạn In-Memory Vector Search trên RAM Lambda
* **Hiện trạng PoC:** 
  DynamoDB là cơ sở dữ liệu NoSQL dạng tài liệu/khóa-giá trị, không hỗ trợ tính toán vector similarity (ANN). Để thực hiện Hybrid Search, AgentSys áp dụng kỹ thuật Two-Stage Search: Bedrock đóng vai trò Query Planner trích xuất `category` để lọc nhanh qua DynamoDB GSI (`category-index`), sau đó kéo một nhóm ứng viên (Candidate Pool giới hạn tối đa 100 bản ghi mới nhất) về bộ nhớ RAM của Lambda API để tính Cosine Similarity bằng Python.
* **Đánh giá hạn chế:** 
  Giải pháp này hoàn toàn miễn phí duy trì cơ sở hạ tầng (không tốn chi phí cụm vector database chạy liên tục). Tuy nhiên, khi quy mô catalog vượt quá hàng chục nghìn bản ghi, việc giới hạn 100 ứng viên sẽ gây ra hiện tượng bỏ sót dữ liệu (recall drop) đối với các file cũ hơn. Nếu quét toàn bộ bảng (Full Table Scan), chi phí RCU của DynamoDB và thời gian thực thi của Lambda sẽ tăng tuyến tính $O(N)$.
* **Giải pháp Enterprise chuẩn AWS:**
  - Tích hợp **Amazon OpenSearch Serverless (Vector Engine)** hoặc **Amazon Aurora Serverless (PostgreSQL với extension `pgvector`)**.
  - Các vector 256-d/1024-d sẽ được lưu trữ và lập chỉ mục bằng thuật toán HNSW (Hierarchical Navigable Small World) hoặc IVF. Khi người dùng truy vấn, phép tính k-NN diễn ra trực tiếp ở tầng lưu trữ với độ trễ dưới 20ms mà không cần tải dữ liệu thô vào RAM của hàm tính toán Lambda.

---

### 2. Kỹ thuật nén chiều Vector & Nâng cấp Titan Embeddings V2
* **Hiện trạng PoC:** 
  Trong các phiên bản đầu, việc giảm chiều vector từ 1536-d xuống 256-d được thực hiện thông qua việc lấy mẫu bước nhảy (uniform striding) nhằm tiết kiệm không gian lưu trữ và giới hạn kích thước document trên DynamoDB (tối đa 400KB/item).
* **Đánh giá hạn chế:** 
  Các chiều trong không gian tiềm ẩn (latent space) của mạng nơ-ron sâu không có tính độc lập tuyến tính. Việc trích xuất thô bạo có thể làm méo mó cấu trúc tô-pô ngữ nghĩa (semantic manifold), ảnh hưởng đến độ phân định của điểm Cosine Similarity.
* **Giải pháp Enterprise chuẩn AWS:**
  - Hệ thống đã được nâng cấp hỗ trợ **Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`)**. Mô hình V2 hỗ trợ cơ chế nén chiều tự nhiên (Matryoshka Representation Learning) cho phép chỉ định trực tiếp `dimensions: 256` kèm theo chuẩn hóa L2 (`normalize: true`) ngay từ API Bedrock.
  - Trong tương lai, việc kết hợp **Amazon Titan Multimodal Embeddings** sẽ cho phép sinh vector trực tiếp từ hình ảnh và video frame, hợp nhất vector hình ảnh và văn bản vào cùng một không gian đa chiều duy nhất.

---

### 3. Mô hình dữ liệu DynamoDB và Xử lý phân mảnh (Single-Table Design)
* **Hiện trạng PoC:** 
  Bảng `AgentSysMediaMetadata` được cấu hình với Partition Key đơn (`file_id`). Khi mở rộng tính năng băm nhỏ bài giảng âm thanh dài thành các đoạn nhỏ (chunking), các chunk được lưu trữ với khóa `file_id = f"{file_id}#CHUNK#{index}"`. Do thiếu Sort Key chuyên biệt, hàm gom chunk (`get_file_chunks`) buộc phải áp dụng biểu thức lọc (FilterExpression).
* **Đánh giá hạn chế:** 
  Việc sử dụng FilterExpression trên bảng không có Sort Key tiêu tốn dung lượng đọc (RCU) vì DynamoDB vẫn phải đọc toàn bộ khối dữ liệu trước khi lọc bỏ.
* **Giải pháp Enterprise chuẩn AWS:**
  - Tái cấu trúc bảng theo mô hình **DynamoDB Single-Table Design chuẩn hóa**:
    - **Partition Key (`PK`):** `FILE#<file_id>`
    - **Sort Key (`SK`):** `METADATA` (cho bản ghi file chính) hoặc `CHUNK#<index>` (cho từng phân đoạn bài giảng).
  - Khi cần tổng hợp dữ liệu bài giảng, Lambda chỉ cần thực hiện 1 truy vấn duy nhất:
    `Query(PK="FILE#123", SK begins_with "CHUNK#")`. Thao tác này đạt độ phức tạp $O(k)$ hoàn hảo, truy xuất chính xác các chunk cần thiết mà không phải scan bất kỳ bản ghi thừa nào.

---

### 4. Điều phối Map-Reduce cho bài giảng âm thanh lớn
* **Hiện trạng PoC:** 
  Khi Amazon Transcribe hoàn tất, sự kiện EventBridge kích hoạt worker Lambda xử lý tóm tắt và gom cụm tuần tự qua các chunk, đồng thời kích hoạt luồng DynamoDB Stream để kiểm chứng tính bất biến và chống race condition bằng `ConditionExpression`.
* **Đánh giá hạn chế:** 
  Nếu file âm thanh là bài giảng dài từ 60 đến 120 phút (tạo ra 40–80 chunks), việc gọi mô hình Bedrock tuần tự trong một hàm Lambda duy nhất có thể chạm ngưỡng giới hạn thời gian chạy (Lambda Timeout 120s – 900s).
* **Giải pháp Enterprise chuẩn AWS:**
  - Thay thế vòng lặp xử lý nội bộ bằng **AWS Step Functions với Distributed Map State**:
    1. **State 1 (Split):** Lambda chia nhỏ transcript thành 50 chunks và lưu vào S3/DynamoDB.
    2. **State 2 (Distributed Map):** Step Functions tự động phân tán (fan-out) đồng thời 50 Lambda workers chạy song song, mỗi worker gọi Bedrock xử lý độc lập cho 1 chunk trong 2 giây.
    3. **State 3 (Reduce):** Tự động gom (fan-in) kết quả từ 50 chunks và gọi hàm Aggregator Lambda tổng hợp bản tóm tắt hoàn chỉnh.
  - Mô hình này giảm thời gian xử lý toàn bộ bài giảng 2 tiếng từ **5 phút xuống còn dưới 10 giây**, đồng thời loại bỏ triệt để nguy cơ Lambda timeout.

---

### 📊 Bảng so sánh tổng hợp: Kiến trúc PoC vs Kiến trúc Enterprise Production

| Tiêu chí kỹ thuật | Kiến trúc PoC hiện tại (AgentSys) | Kiến trúc Enterprise AWS đề xuất |
| :--- | :--- | :--- |
| **Cơ chế Vector Search** | Candidate Pool (100 items) + Cosine RAM Lambda | Amazon OpenSearch Serverless / pgvector (HNSW Index) |
| **Không gian Embeddings** | Titan V2 (256-d) + Fallback Titan V1 Striding | Titan Multimodal Embeddings V2 Native (256-d / 1024-d) |
| **Cấu trúc dữ liệu** | Single PK (`file_id`) + FilterExpression | Composite Primary Key (`PK: FILE#id`, `SK: CHUNK#idx`) |
| **Xử lý Map-Reduce** | EventBridge Worker + DynamoDB Streams Demo | AWS Step Functions (Distributed Map State) |
| **Độ trễ xử lý âm thanh** | Tuyến tính $O(N)$ theo số chunks | Song song $O(1)$ phân tán đồng thời |
| **Chi phí hạ tầng nhàn rỗi** | **$0.00 / tháng** (Zero-Idle Serverless) | ~$20–$50 / tháng (OpenSearch Serverless OCU tối thiểu) |
| **Mục tiêu tối ưu** | Tiết kiệm chi phí thực nghiệm, dễ debug, bảo vệ PoC | Độ tin cậy cao, mở rộng hàng triệu files, SLA doanh nghiệp |
