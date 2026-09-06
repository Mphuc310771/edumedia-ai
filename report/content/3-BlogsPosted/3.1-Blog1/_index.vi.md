---
title: "Blog 1"
date: 2024-01-01
weight: 1
chapter: false
pre: " <b> 3.1. </b> "
---

# Blog 1: Kinh nghiệm dùng Amazon Rekognition bóc tách chữ và phân loại ảnh bài giảng

Khi bắt tay vào làm dự án **AgentSys** (hệ thống tìm kiếm tài liệu học tập đa phương tiện cho sinh viên), bài toán đầu tiên mình phải giải quyết là: **Làm sao để tìm được một bức ảnh chụp bảng giảng đường hay slide bài thuyết trình khi người dùng gõ từ khóa?**

Ban đầu, mình tính tự dựng model OCR (như PaddleOCR hoặc EasyOCR) rồi deploy lên EC2. Nhưng tính đi tính lại, sinh viên đâu phải lúc nào cũng upload ảnh 24/7. Thuê một con EC2 có GPU rẻ nhất cũng tốn ~$40–$50/tháng chỉ để ngồi chờ request. Vì vậy, mình quyết định chuyển hẳn sang dùng **Amazon Rekognition** theo mô hình Serverless.

Dưới đây là một số kinh nghiệm thực tế mình rút ra được khi tích hợp dịch vụ này.

---

## 1. Kết hợp đồng thời DetectLabels và DetectText

Để lập chỉ mục (index) đầy đủ cho một bức ảnh tài liệu học tập, chỉ đọc chữ (OCR) hoặc chỉ nhận diện đồ vật là không đủ:
* Nếu chỉ dùng `DetectText`: Ảnh chụp chú chó đi dạo trong sân trường hay ảnh lễ tốt nghiệp không có chữ sẽ bị bỏ qua, không phân loại được.
* Nếu chỉ dùng `DetectLabels`: Ảnh chụp bảng viết đầy công thức Toán ma trận sẽ chỉ được gắn nhãn chung chung là `Text`, `Blackboard`, không tìm kiếm được nội dung chi tiết bên trong.

Vì vậy trong hàm Lambda `agentsys-ingest`, mình gọi song song cả 2 API:

```python
# Gọi DetectLabels để phân loại danh mục (Category)
labels_res = rekognition.detect_labels(
    Image={"S3Object": {"Bucket": bucket, "Name": key}},
    MaxLabels=10,
    MinConfidence=70.0
)

# Gọi DetectText để lấy nội dung bài giảng phục vụ tìm kiếm
text_res = rekognition.detect_text(
    Image={"S3Object": {"Bucket": bucket, "Name": key}}
)
```

---

## 2. Vấn đề thực tế: Lọc nhiễu OCR từ bảng viết tay

Khi thử nghiệm với ảnh chụp bảng phấn giảng đường thực tế, mình gặp một vấn đề: `DetectText` trả về rất nhiều đoạn text vụn vặt (các nét phấn mờ, ký tự rác chỉ có 1–2 ký tự ngẫu nhiên). Nếu lưu hết đống rác này vào DynamoDB, vector embedding sẽ bị loãng và tìm kiếm dễ bị sai.

Để giải quyết, mình viết thêm một hàm lọc nhiễu đơn giản trong `apps/domain.py`:

```python
def is_noise_ocr_line(text: str) -> bool:
    """Lọc bỏ các dòng chữ rác không có ý nghĩa ngữ nghĩa"""
    clean = text.strip()
    # Bỏ qua các ký tự đơn lẻ hoặc chuỗi toàn ký tự đặc biệt
    if len(clean) <= 1:
        return True
    if clean.isdigit() and len(clean) < 3:
        return True
    return False
```

Nhờ đoạn lọc này, dữ liệu lưu vào DynamoDB sạch hơn hẳn, chỉ giữ lại các dòng văn bản thực sự có ý nghĩa như tên đề mục, công thức, hoặc lời giảng trên slide.

---

## 3. Tối ưu chi phí thực tế

* Mỗi ảnh chạy cả `DetectLabels` ($0.001) + `DetectText` ($0.001) tốn tổng cộng **$0.002 (khoảng 50 VNĐ)**.
* Với 1.000 ảnh miễn phí mỗi tháng trong AWS Free Tier, toàn bộ quá trình phát triển và kiểm thử đồ án của mình hoàn toàn không tốn một đồng nào.
* Tốc độ xử lý trung bình qua Lambda chỉ mất khoảng **400ms – 600ms** cho một ảnh 4K.

---

## 4. Tóm lại

Nếu bạn đang làm đồ án hoặc dự án vừa và nhỏ cần xử lý ảnh mà không muốn bận tâm đến việc bảo trì máy chủ hay quản lý model ML, Amazon Rekognition là một lựa chọn cực kỳ kinh tế và tiện lợi. Chỉ cần vài dòng code Python với Boto3 là đã có ngay tính năng nhận diện ảnh chuẩn production.
