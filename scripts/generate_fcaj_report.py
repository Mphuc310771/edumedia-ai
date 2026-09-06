"""Generate remaining FCAJ report pages (bilingual, AgentSys). Run from repo root."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "report" / "content"


def w(rel: str, text: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


WEEKS = [
    {
        "n": 1,
        "folder": "1.1-Week1",
        "pre": "1.1.",
        "start": "01/06/2026",
        "end": "07/06/2026",
        "title_en": "Week 1 — AWS fundamentals & AgentSys scope",
        "title_vi": "Tuần 1 — Nền tảng AWS và phạm vi AgentSys",
        "obj_en": [
            "Meet FCAJ mentors and internship rules.",
            "Use AWS Management Console and AWS CLI (identity, region, budgets).",
            "Define AgentSys: a lecture library that reads images/audio instead of filenames.",
        ],
        "obj_vi": [
            "Làm quen mentor FCAJ và nội quy thực tập.",
            "Dùng AWS Console và AWS CLI (identity, region, budgets).",
            "Chốt phạm vi AgentSys: thư viện bài giảng đọc nội dung ảnh/audio thay vì nhớ tên file.",
        ],
        "tasks_en": [
            ("Mon", "Read FCAJ project rules (workshop website, bilingual report, 3 blogs). Review AgentSys README.", "01/06/2026"),
            ("Tue", "Create/confirm AWS account, IAM user with MFA, `aws configure`, `aws sts get-caller-identity`.", "02/06/2026"),
            ("Wed", "Map service groups: compute (Lambda), storage (S3), database (DynamoDB), AI (Rekognition, Transcribe, Bedrock).", "03/06/2026"),
            ("Thu", "Scaffold FastAPI (`apps/api`) + React Vite (`gallery_web`). Pydantic settings from `.env`.", "04/06/2026"),
            ("Fri", "Health endpoint + CORS for localhost:5174. First pytest skeleton.", "06/06/2026"),
        ],
        "tasks_vi": [
            ("T2", "Đọc quy định project FCAJ (website workshop, báo cáo 2 ngôn ngữ, 3 blog). Rà soát README AgentSys.", "01/06/2026"),
            ("T3", "Tài khoản AWS, IAM MFA, `aws configure`, `aws sts get-caller-identity`.", "02/06/2026"),
            ("T4", "Nhóm dịch vụ: Lambda, S3, DynamoDB, Rekognition, Transcribe, Bedrock.", "03/06/2026"),
            ("T5", "Skeleton FastAPI + React Vite. Pydantic Settings đọc `.env`.", "04/06/2026"),
            ("T6", "Endpoint `/health`, CORS Vite. Pytest tối thiểu.", "06/06/2026"),
        ],
        "res_en": "CLI works; empty UI loads; `/health` returns JSON. Chose **serverless + managed AI**, not EC2/RDS, to stay inside program credits.",
        "res_vi": "CLI chạy; UI trống load được; `/health` trả JSON. Chọn **serverless + AI managed**, không EC2/RDS, để giữ credit.",
    },
    {
        "n": 2,
        "folder": "1.2-Week2",
        "pre": "1.2.",
        "start": "08/06/2026",
        "end": "14/06/2026",
        "title_en": "Week 2 — Domain model and subject taxonomy",
        "title_vi": "Tuần 2 — Domain model và taxonomy môn học",
        "obj_en": ["Model MediaRecord.", "Write `apps/taxonomy.yaml` for categories and CNTT vs off-major subjects."],
        "obj_vi": ["Mô hình MediaRecord.", "Viết `apps/taxonomy.yaml` cho danh mục và môn ngành / ngoài ngành."],
        "tasks_en": [
            ("Mon", "Fields: file_id, s3_key, labels, ocr_text, transcript, category, subject, status INDEXING/READY/FAILED.", "08/06/2026"),
            ("Wed", "Weighted keywords for math, OS, networks, programming, cloud, English, …", "10/06/2026"),
            ("Fri", "Unit tests for infer_category / infer_subject from OCR snippets (integral, Round Robin).", "12/06/2026"),
        ],
        "tasks_vi": [
            ("T2", "Trường dữ liệu: file_id, s3_key, labels, ocr, transcript, category, subject, status.", "08/06/2026"),
            ("T4", "Từ khóa có trọng số: toán, HĐH, mạng, lập trình, cloud, tiếng Anh, …", "10/06/2026"),
            ("T6", "Test phân loại từ snippet OCR (tích phân, Round Robin).", "12/06/2026"),
        ],
        "res_en": "Classification no longer depends on a local GPU. Taxonomy is data, not hardcoded if-else in the UI.",
        "res_vi": "Phân loại không cần GPU local. Taxonomy là dữ liệu, không hard-code if-else trên UI.",
    },
    {
        "n": 3,
        "folder": "1.3-Week3",
        "pre": "1.3.",
        "start": "15/06/2026",
        "end": "21/06/2026",
        "title_en": "Week 3 — Private S3 and presigned uploads",
        "title_vi": "Tuần 3 — S3 private và presigned upload",
        "obj_en": ["Bucket never public.", "Browser PUT via presigned URL.", "SSE-S3."],
        "obj_vi": ["Bucket không public.", "Trình duyệt PUT qua presigned URL.", "SSE-S3."],
        "tasks_en": [
            ("Mon", "Create private bucket, block public ACLs, CORS for Vite origin.", "15/06/2026"),
            ("Wed", "`POST /upload-url` returns file_id + presigned PUT. Frontend `putPresigned`.", "17/06/2026"),
            ("Fri", "Confirm object in console; GET via presign for gallery preview.", "19/06/2026"),
        ],
        "tasks_vi": [
            ("T2", "Bucket private, chặn public ACL, CORS origin Vite.", "15/06/2026"),
            ("T4", "`POST /upload-url` trả file_id + PUT presign. UI `putPresigned`.", "17/06/2026"),
            ("T6", "Object hiện trên console; GET presign để xem trong gallery.", "19/06/2026"),
        ],
        "res_en": "No static access keys in the browser. Upload path matches production Lambda later.",
        "res_vi": "Không nhét access key vào trình duyệt. Luồng upload khớp Lambda production.",
    },
    {
        "n": 4,
        "folder": "1.4-Week4",
        "pre": "1.4.",
        "start": "22/06/2026",
        "end": "28/06/2026",
        "title_en": "Week 4 — Amazon Rekognition DetectLabels + DetectText",
        "title_vi": "Tuần 4 — Amazon Rekognition DetectLabels + DetectText",
        "obj_en": ["OCR lecture boards.", "Labels for non-study photos (pets, receipts)."],
        "obj_vi": ["OCR bảng giảng.", "Nhãn cho ảnh không phải bài học (thú cưng, hóa đơn)."],
        "tasks_en": [
            ("Tue", "IAM: rekognition:DetectLabels, DetectText on ingest role only.", "23/06/2026"),
            ("Thu", "Wire `analyze_image` in ingest; map labels to Vietnamese tags; feed OCR to taxonomy.", "25/06/2026"),
            ("Fri", "Test with a calculus board photo vs a dog photo — subjects must differ.", "26/06/2026"),
        ],
        "tasks_vi": [
            ("T3", "IAM: DetectLabels, DetectText chỉ trên role ingest.", "23/06/2026"),
            ("T5", "`analyze_image`; dịch nhãn; đẩy OCR vào taxonomy.", "25/06/2026"),
            ("T6", "Thử ảnh bảng tích phân vs ảnh chó — môn/danh mục phải khác.", "26/06/2026"),
        ],
        "res_en": "Images become searchable text. Cost Explorer later showed Rekognition as the main lab spend (~$0.08) — concurrency must stay low.",
        "res_vi": "Ảnh thành văn bản tìm được. Cost Explorer cho thấy Rekognition là khoản lab chính (~$0.08) — phải giữ concurrency thấp.",
    },
    {
        "n": 5,
        "folder": "1.5-Week5",
        "pre": "1.5.",
        "start": "29/06/2026",
        "end": "05/07/2026",
        "title_en": "Week 5 — Amazon Transcribe vi-VN and EventBridge",
        "title_vi": "Tuần 5 — Amazon Transcribe vi-VN và EventBridge",
        "obj_en": ["Do not block HTTP for 3-minute jobs.", "Vietnamese lecture audio."],
        "obj_vi": ["Không block HTTP chờ job 3 phút.", "Audio bài giảng tiếng Việt."],
        "tasks_en": [
            ("Mon", "StartTranscriptionJob language vi-VN; store job name on the record.", "29/06/2026"),
            ("Wed", "EventBridge rule source aws.transcribe COMPLETED/FAILED → ingest Lambda.", "01/07/2026"),
            ("Fri", "UI: INDEXING badge + poll /status. Health detects SubscriptionRequired.", "03/07/2026"),
        ],
        "tasks_vi": [
            ("T2", "StartTranscriptionJob language vi-VN; lưu job name trên record.", "29/06/2026"),
            ("T4", "Rule EventBridge aws.transcribe COMPLETED/FAILED → ingest Lambda.", "01/07/2026"),
            ("T6", "UI badge INDEXING + poll /status. Health bắt SubscriptionRequired.", "03/07/2026"),
        ],
        "res_en": "Async speech path. If Transcribe is not enabled on the account, UI says DEGRADED instead of hanging.",
        "res_vi": "Speech async. Account chưa bật Transcribe thì UI DEGRADED, không treo.",
    },
    {
        "n": 6,
        "folder": "1.6-Week6",
        "pre": "1.6.",
        "start": "06/07/2026",
        "end": "12/07/2026",
        "title_en": "Week 6 — DynamoDB catalog and category-index GSI",
        "title_vi": "Tuần 6 — Catalog DynamoDB và GSI category-index",
        "obj_en": ["On-demand table, PK file_id, GSI on category."],
        "obj_vi": ["Bảng on-demand, PK file_id, GSI category."],
        "tasks_en": [
            ("Tue", "PutItem after ingest; Scan list for lab size; Query GSI for category tabs.", "07/07/2026"),
            ("Thu", "PITR off for lab cost. IAM scoped to table + index ARN.", "09/07/2026"),
        ],
        "tasks_vi": [
            ("T3", "PutItem sau ingest; Scan list lab; Query GSI cho tab danh mục.", "07/07/2026"),
            ("T5", "Tắt PITR cho lab. IAM chỉ table + index ARN.", "09/07/2026"),
        ],
        "res_en": "Catalog survives Lambda restarts. No RDS/NAT bill.",
        "res_vi": "Catalog sống qua lần restart Lambda. Không hóa đơn RDS/NAT.",
    },
    {
        "n": 7,
        "folder": "1.7-Week7",
        "pre": "1.7.",
        "start": "13/07/2026",
        "end": "19/07/2026",
        "title_en": "Week 7 — Bedrock Nova Lite planner and Titan embeddings",
        "title_vi": "Tuần 7 — Bedrock Nova Lite planner và Titan embeddings",
        "obj_en": ["Natural Vietnamese query → search plan.", "Hybrid keyword + cosine. No fake vectors."],
        "obj_vi": ["Câu tiếng Việt → kế hoạch tìm.", "Lai từ khóa + cosine. Không vector giả."],
        "tasks_en": [
            ("Mon", "Converse Nova Lite JSON plan (keywords, media_type, subject, rationale).", "13/07/2026"),
            ("Wed", "Titan embed on ingest; hybrid_search weights; cooldown on daily token cap.", "15/07/2026"),
            ("Fri", "Acceptance: “Tìm đoạn thầy dặn thi cuối kỳ” hits Round Robin audio.", "17/07/2026"),
        ],
        "tasks_vi": [
            ("T2", "Converse Nova Lite ra JSON plan (keywords, media_type, subject, rationale).", "13/07/2026"),
            ("T4", "Titan embed khi ingest; hybrid_search; cooldown khi hết token/ngày.", "15/07/2026"),
            ("T6", "Nghiệm thu: “Tìm đoạn thầy dặn thi cuối kỳ” ra audio Round Robin.", "17/07/2026"),
        ],
        "res_en": "Agent query is a real Bedrock call with heuristic fallback — matches FCAJ AI theme.",
        "res_vi": "Agent query gọi Bedrock thật, fallback heuristic — đúng chủ đề Cloud AI.",
    },
    {
        "n": 8,
        "folder": "1.8-Week8",
        "pre": "1.8.",
        "start": "20/07/2026",
        "end": "26/07/2026",
        "title_en": "Week 8 — AWS SAM, SQS + DLQ, least-privilege IAM",
        "title_vi": "Tuần 8 — AWS SAM, SQS + DLQ, IAM least-privilege",
        "obj_en": ["Repeatable deploy. S3 → SQS → ingest, not S3 → Lambda directly."],
        "obj_vi": ["Deploy lặp lại được. S3 → SQS → ingest, không S3 → Lambda trực tiếp."],
        "tasks_en": [
            ("Mon", "infra/template.yaml: queues, functions, HttpApi, table, bucket notify.", "20/07/2026"),
            ("Wed", "DLQ maxReceiveCount 3. Ingest reserved concurrency 2.", "22/07/2026"),
            ("Fri", "`sam build -t infra/template.yaml` && `sam deploy --guided --capabilities CAPABILITY_IAM`.", "24/07/2026"),
        ],
        "tasks_vi": [
            ("T2", "template.yaml: queue, function, HttpApi, table, notify bucket.", "20/07/2026"),
            ("T4", "DLQ maxReceiveCount 3. Ingest reserved concurrency 2.", "22/07/2026"),
            ("T6", "`sam build` và `sam deploy --guided --capabilities CAPABILITY_IAM`.", "24/07/2026"),
        ],
        "res_en": "No `AWS_ACCESS_KEY_ID` in the template. Burst uploads cannot stampede Rekognition.",
        "res_vi": "Không có `AWS_ACCESS_KEY_ID` trong template. Upload ồ ạt không đốt Rekognition.",
    },
    {
        "n": 9,
        "folder": "1.9-Week9",
        "pre": "1.9.",
        "start": "27/07/2026",
        "end": "02/08/2026",
        "title_en": "Week 9 — CloudWatch, health pings, API key",
        "title_vi": "Tuần 9 — CloudWatch, health ping, API key",
        "obj_en": ["Logs, custom metrics, alarms, real health, X-API-Key / Cognito bearer path."],
        "obj_vi": ["Log, metric tự định nghĩa, alarm, health thật, X-API-Key / Cognito bearer."],
        "tasks_en": [
            ("Tue", "Namespace AgentSys: MediaIngested, MediaIngestFailed. Four alarms including DLQ depth.", "28/07/2026"),
            ("Thu", "`ping_aws` for STS/S3/DDB/Rekognition/Transcribe/Bedrock. UI status is not decorative.", "30/07/2026"),
            ("Fri", "Log retention 14 days. Rate limit agent/query.", "31/07/2026"),
        ],
        "tasks_vi": [
            ("T3", "Namespace AgentSys: MediaIngested, MediaIngestFailed. Bốn alarm kể cả DLQ.", "28/07/2026"),
            ("T5", "`ping_aws` từng service. Thanh trạng thái UI không trang trí.", "30/07/2026"),
            ("T6", "Log 14 ngày. Rate limit agent/query.", "31/07/2026"),
        ],
        "res_en": "Failed Transcribe jobs surface as FAILED + alarm, not silent SQS retries forever.",
        "res_vi": "Job Transcribe lỗi hiện FAILED + alarm, không retry SQS im lặng mãi.",
    },
    {
        "n": 10,
        "folder": "1.10-Week10",
        "pre": "1.10.",
        "start": "03/08/2026",
        "end": "09/08/2026",
        "title_en": "Week 10 — Tests, UI, background ingest",
        "title_vi": "Tuần 10 — Test, UI, ingest chạy nền",
        "obj_en": ["CI pytest + frontend build. Upload must not freeze the browser."],
        "obj_vi": ["CI pytest + build frontend. Upload không được treo trình duyệt."],
        "tasks_en": [
            ("Mon", "Fake AWS runtime for pytest (34 tests). GitHub Actions.", "03/08/2026"),
            ("Wed", "BackgroundTasks /process; parallel upload queue; reprocess FAILED.", "05/08/2026"),
            ("Fri", "Local filter vs Enter for Bedrock. Multi-select delete.", "07/08/2026"),
        ],
        "tasks_vi": [
            ("T2", "Fake AWS cho pytest. GitHub Actions.", "03/08/2026"),
            ("T4", "BackgroundTasks /process; hàng đợi upload song song; reprocess FAILED.", "05/08/2026"),
            ("T6", "Lọc local vs Enter Bedrock. Chọn nhiều để xóa.", "07/08/2026"),
        ],
        "res_en": "Lab is usable while Transcribe runs. CI guards regressions without calling paid APIs.",
        "res_vi": "Lab dùng được khi Transcribe đang chạy. CI không gọi API trả phí.",
    },
    {
        "n": 11,
        "folder": "1.11-Week11",
        "pre": "1.11.",
        "start": "10/08/2026",
        "end": "16/08/2026",
        "title_en": "Week 11 — Blogs, cost control, report site",
        "title_vi": "Tuần 11 — Blog, kiểm soát chi phí, website báo cáo",
        "obj_en": ["Three Study Group blogs. Cost Explorer. Hugo report from official template."],
        "obj_vi": ["Ba bài blog AWS Study Group. Cost Explorer. Website Hugo theo template chính thức."],
        "tasks_en": [
            ("Mon", "Draft blogs: presigned S3, event-driven ingest, Bedrock cost fallback.", "10/08/2026"),
            ("Wed", "Read Credits + Cost Explorer (Rekognition $0.08). Stop idle local health pings.", "12/08/2026"),
            ("Fri", "Hugo Learn site: bilingual sections matching fcj-workshop-template.", "14/08/2026"),
        ],
        "tasks_vi": [
            ("T2", "Nháp blog: S3 presign, ingest event-driven, Bedrock fallback chi phí.", "10/08/2026"),
            ("T4", "Credits + Cost Explorer (Rekognition $0.08). Tắt ping health local khi không demo.", "12/08/2026"),
            ("T6", "Site Hugo Learn song ngữ, đúng fcj-workshop-template.", "14/08/2026"),
        ],
        "res_en": "Billing literacy: estimated credits ≠ live meter. Report structure unblocks grading.",
        "res_vi": "Đọc billing: estimated credit không phải đồng hồ đang chạy. Đủ cấu trúc để chấm.",
    },
    {
        "n": 12,
        "folder": "1.12-Week12",
        "pre": "1.12.",
        "start": "17/08/2026",
        "end": "23/08/2026",
        "title_en": "Week 12 — Cleanup, demo, submission",
        "title_vi": "Tuần 12 — Dọn resource, demo, nộp bài",
        "obj_en": ["Empty S3, sam delete, demo video, fill personal fields and event photos."],
        "obj_vi": ["Empty S3, sam delete, video demo, điền SĐT/ảnh event."],
        "tasks_en": [
            ("Mon", "`aws s3 rm --recursive` then `sam delete --stack-name agentsys`. Confirm console empty.", "17/08/2026"),
            ("Wed", "Record demo: upload image, OCR, query Round Robin, show CloudWatch alarm screenshot.", "19/08/2026"),
            ("Fri", "Publish GitHub Pages report. Post 3 blogs to AWS Study Group. Submit links.", "21/08/2026"),
        ],
        "tasks_vi": [
            ("T2", "`aws s3 rm --recursive` rồi `sam delete --stack-name agentsys`. Console trống.", "17/08/2026"),
            ("T4", "Quay demo: upload ảnh, OCR, query Round Robin, chụp alarm CloudWatch.", "19/08/2026"),
            ("T6", "Pages báo cáo. Đăng 3 blog nhóm Study Group. Nộp link.", "21/08/2026"),
        ],
        "res_en": "Lifecycle closed: build → run → measure → destroy. Credits stop growing after delete.",
        "res_vi": "Khép vòng đời: dựng → chạy → đo → xóa. Credit ngừng tăng sau delete.",
    },
]


def week_en(w0: dict) -> str:
    rows = "\n".join(
        f"| {d} | {t} | {s} | {s} | AgentSys repo / AWS docs |"
        for d, t, s in w0["tasks_en"]
    )
    objs = "\n".join(f"* {x}" for x in w0["obj_en"])
    return f"""
---
title: "{w0['title_en']}"
date: 2026-06-01
weight: {w0['n']}
chapter: false
pre: " {w0['pre']} "
---

### Week {w0['n']} objectives

{objs}

Period: **{w0['start']} – {w0['end']}**

### Tasks this week

| Day | Task | Start | Done | Reference |
| --- | --- | --- | --- | --- |
{rows}

### Results

{w0['res_en']}

![Screenshot placeholder — paste Console / UI capture here](/images/worklog/week{w0['n']}.png)
"""


def week_vi(w0: dict) -> str:
    rows = "\n".join(
        f"| {d} | {t} | {s} | {s} | Repo AgentSys / tài liệu AWS |"
        for d, t, s in w0["tasks_vi"]
    )
    objs = "\n".join(f"* {x}" for x in w0["obj_vi"])
    return f"""
---
title: "{w0['title_vi']}"
date: 2026-06-01
weight: {w0['n']}
chapter: false
pre: " {w0['pre']} "
---

### Mục tiêu tuần {w0['n']}

{objs}

Thời gian: **{w0['start']} – {w0['end']}**

### Công việc trong tuần

| Thứ | Công việc | Bắt đầu | Xong | Tài liệu |
| --- | --- | --- | --- | --- |
{rows}

### Kết quả đạt được

{w0['res_vi']}

![Chỗ dán ảnh Console / UI](/images/worklog/week{w0['n']}.png)
"""


def main() -> None:
    w("1-Worklog/_index.md", """
---
title: "Worklog"
date: 2026-06-01
weight: 1
chapter: false
pre: " 1. "
---

This worklog covers **12 weeks** of the First Cloud AI Journey internship (01/06/2026 – 23/08/2026). Each week pairs an AWS skill with a slice of **AgentSys** (personal serverless lecture library).

**Week 1:** [AWS fundamentals & AgentSys scope](1.1-Week1/)

**Week 2:** [Domain model and subject taxonomy](1.2-Week2/)

**Week 3:** [Private S3 and presigned uploads](1.3-Week3/)

**Week 4:** [Rekognition DetectLabels + DetectText](1.4-Week4/)

**Week 5:** [Transcribe vi-VN and EventBridge](1.5-Week5/)

**Week 6:** [DynamoDB catalog and GSI](1.6-Week6/)

**Week 7:** [Bedrock planner and Titan embeddings](1.7-Week7/)

**Week 8:** [SAM, SQS + DLQ, IAM](1.8-Week8/)

**Week 9:** [CloudWatch, health, API key](1.9-Week9/)

**Week 10:** [Tests, UI, background ingest](1.10-Week10/)

**Week 11:** [Blogs, cost, report website](1.11-Week11/)

**Week 12:** [Cleanup, demo, submission](1.12-Week12/)
""")
    w("1-Worklog/_index.vi.md", """
---
title: "Worklog"
date: 2026-06-01
weight: 1
chapter: false
pre: " 1. "
---

Nhật ký **12 tuần** First Cloud AI Journey (01/06/2026 – 23/08/2026). Mỗi tuần gắn một kỹ năng AWS với một phần **AgentSys** (thư viện bài giảng serverless, dự án cá nhân).

**Tuần 1:** [Nền tảng AWS và phạm vi AgentSys](1.1-Week1/)

**Tuần 2:** [Domain model và taxonomy môn học](1.2-Week2/)

**Tuần 3:** [S3 private và presigned upload](1.3-Week3/)

**Tuần 4:** [Rekognition DetectLabels + DetectText](1.4-Week4/)

**Tuần 5:** [Transcribe vi-VN và EventBridge](1.5-Week5/)

**Tuần 6:** [Catalog DynamoDB và GSI](1.6-Week6/)

**Tuần 7:** [Bedrock planner và Titan embeddings](1.7-Week7/)

**Tuần 8:** [SAM, SQS + DLQ, IAM](1.8-Week8/)

**Tuần 9:** [CloudWatch, health, API key](1.9-Week9/)

**Tuần 10:** [Test, UI, ingest nền](1.10-Week10/)

**Tuần 11:** [Blog, chi phí, website báo cáo](1.11-Week11/)

**Tuần 12:** [Dọn resource, demo, nộp bài](1.12-Week12/)
""")
    for item in WEEKS:
        w(f"1-Worklog/{item['folder']}/_index.md", week_en(item))
        w(f"1-Worklog/{item['folder']}/_index.vi.md", week_vi(item))

    print("weeks ok")


if __name__ == "__main__":
    main()
