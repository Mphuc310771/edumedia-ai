---
title: "Blog 2"
date: 2024-01-01
weight: 2
chapter: false
pre: " <b> 3.2. </b> "
---

# Blog 2: Bóc băng tiếng Việt với Amazon Transcribe: Tránh bẫy Timeout và Vòng lặp S3

Trong dự án **AgentSys**, một trong những tính năng "ăn tiền" nhất là giúp sinh viên tìm kiếm bài giảng dựa trên lời nói của giảng viên (ví dụ: gõ *"thầy dặn thi cuối kỳ làm bài tập nào"* là tìm ra ngay đoạn ghi âm liên quan).

Để làm tính năng này, mình chọn **Amazon Transcribe** vì nó có sẵn model tiếng Việt (`vi-VN`) với độ chính xác khá ấn tượng. Tuy nhiên, trong quá trình tích hợp vào kiến trúc Serverless, mình đã vấp phải 2 "cú lừa" kinh điển về mặt hệ thống mà nếu không cẩn thận sẽ làm sập Lambda hoặc gây cháy túi tài khoản AWS.

---

## 1. Bẫy số 1: Đồng bộ hóa tác vụ bóc băng gây Timeout

Ban đầu, mình viết code Lambda theo luồng tuần tự (Synchronous):
1. Nhận file audio tải lên.
2. Gọi `start_transcription_job()`.
3. Dùng vòng lặp `while True` với `time.sleep(5)` để chờ Job chuyển sang `COMPLETED`.
4. Lấy kết quả lưu vào DynamoDB.

**Hậu quả:**  
Khi test với file ghi âm ngắn 15 giây thì mọi thứ chạy mượt mà. Nhưng khi thử với file bài giảng thực tế dài 3–5 phút, Transcribe mất khoảng 40–60 giây để xử lý xong. Hàm Lambda bị treo chờ, vượt quá giới hạn API Gateway Timeout (29 giây) và ngốn sạch chi phí thời gian chạy của Lambda.

**Cách giải quyết:**  
Chuyển hẳn sang mô hình **Bất đồng bộ (Asynchronous State Machine)**:
* Khi file được tải lên, Lambda Ingest chỉ khởi tạo Transcribe Job rồi ghi ngay một bản ghi vào DynamoDB với trạng thái `status: "INDEXING"`. Phản hồi trả về cho người dùng ngay lập tức (< 1 giây).
* Khi Transcribe hoàn tất, dịch vụ sẽ tự động ghi file kết quả `.json` vào S3. Hệ thống chỉ cần đọc file này và cập nhật trạng thái bản ghi thành `READY`.

---

## 2. Bẫy số 2: Vòng lặp sự kiện đệ quy vô tận trên S3

Đây là lỗi phổ biến nhất khiến nhiều bạn mới làm quen với AWS bị trừ tiền oan:
* Bạn cấu hình S3 Event Notification: *"Cứ có file mới trong bucket là gọi Lambda Ingest"*.
* Người dùng upload `audio.mp3` $\rightarrow$ S3 gọi Lambda $\rightarrow$ Lambda gọi Transcribe.
* Transcribe xử lý xong, lưu kết quả `transcript.json` vào chính bucket đó $\rightarrow$ **S3 lại thấy có file mới, tiếp tục gọi Lambda $\rightarrow$ Lambda lại gọi Transcribe...**

Vòng lặp này lặp đi lặp lại hàng trăm lần trong vài phút!

**Cách khắc phục:**  
Luôn luôn phân vùng thư mục (prefix) rõ ràng trong S3 bucket:
* S3 Event Notification chỉ lắng nghe các file nằm trong thư mục **`uploads/`**.
* Amazon Transcribe được chỉ định lưu file kết quả vào thư mục **`transcripts/`**.

Nhờ phân tách rõ ràng như vậy, file output của Transcribe sẽ không bao giờ kích hoạt lại Lambda Ingest.

---

## 3. Tối ưu độ chính xác cho tiếng Việt

Để Amazon Transcribe nhận diện tiếng Việt chuẩn nhất trong môi trường bài giảng có tạp âm:
* Định dạng file khuyến nghị: Sử dụng định dạng nén nhẹ như `.m4a` (AAC) hoặc `.mp3` thay vì `.wav` nặng nề để giảm thời gian upload.
* Đặt tham số `LanguageCode: "vi-VN"`.
* Chi phí: `$0.024 / phút` (khoảng 600 VNĐ cho 1 phút bóc băng, và có 60 phút miễn phí mỗi tháng trong Free Tier).

---

## 4. Lời kết

Xây dựng hệ thống xử lý audio trên Cloud không chỉ đơn thuần là gọi API, mà quan trọng hơn là **thiết kế luồng dữ liệu bất đồng bộ** để hệ thống hoạt động ổn định, không bị nghẽn và kiểm soát tốt chi phí.
