# Báo cáo thực tập FCAJ (Hugo — template chính thức)

Site này **fork layout** từ [thienluhoan/fcj-workshop-template](https://github.com/thienluhoan/fcj-workshop-template): theme Learn, `themeVariant = workshop`, **7 mục**, **song ngữ vi/en**.

Phần **5. Workshop** là dự án cá nhân **AgentSys** (S3, SQS, Lambda, Rekognition, Transcribe, EventBridge, DynamoDB, Bedrock, CloudWatch, SAM) — **không** copy lab VPC Endpoint / S3 on-prem của mẫu.

Sau khi push `main` (kèm submodule theme), Actions xuất Pages:

**https://mphuc310771.github.io/serverless-multimodal-agent/**

Repo → Settings → Pages → source branch **`gh-pages`**.

## Xem local

Cài [Hugo Extended](https://gohugo.io/installation/) ≥ 0.120:

```bash
git submodule update --init --recursive
cd report
hugo server -D
```

Đính kèm IaC: [template.yaml](/files/template.yaml), [Dockerfile](/files/Dockerfile).

## Việc bạn phải tự điền (rubrik + mộc)

Template không làm hộ được:

| Mục | File | Việc |
|---|---|---|
| 2.1 Thông tin SV | `content/_index.md` + `_index.vi.md` | SĐT, ngành, lớp, ảnh `static/images/avatar.png` |
| 2.2 Worklog | `content/1-Worklog/1.N-WeekN/` | Thay `static/images/worklog/weekN.png` bằng screenshot Console/UI |
| 2.3 Proposal | đã viết AgentSys | Không copy IoT Weather mẫu |
| 2.4 Blogs | `3-BlogsPosted/` | Đăng **3 bài** lên nhóm AWS Study Group, dán URL |
| 2.5 Events | `4-EventParticipated/` | Tên/ngày/địa điểm thật + `static/images/events/eventN.png` |
| 2.6 Workshop | `5-Workshop/` | Screenshot kiến trúc, `sam deploy`, Rekognition, CloudWatch |
| 2.7–2.8 | self-eval / feedback | Đã điền theo AgentSys; sửa nếu không đúng trải nghiệm |
| Mộc | ngoài website | Project xong + báo cáo + ≥ 3 tháng + 10 buổi VP + 3 blog |

## Thang điểm workshop (nhắc nhanh)

Ý tưởng 1.0 · Kiến trúc 2.0 · Step-by-step 2.0 · Tài liệu song ngữ 0.5 · Đóng góp cá nhân 0.5
