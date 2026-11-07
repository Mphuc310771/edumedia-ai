"""AWS test doubles and Moto setup for pytest.

S3, DynamoDB, and CloudWatch use real boto3 operations backed by Moto.
AI services (Vision, Speech, Planner) use lightweight stubs since cloud AI
models require external model execution / live GPUs.
"""
from __future__ import annotations

import re
from typing import List

import boto3

from apps.aws.aws_services import CloudWatchMetrics, DynamoCatalog, S3ObjectStore
from apps.aws.providers import Runtime
from apps.domain import MediaRecord, SearchPlan, infer_subject
from config.settings import settings


SAMPLE_RECORDS = [
    MediaRecord(
        file_id="seed-lecture-board",
        filename="IMG_20260812_091522.jpg",
        s3_key="uploads/seed-lecture-board.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        labels=["Text", "Whiteboard", "Classroom", "Person"],
        ocr_text="Toán Cao Cấp - Chương 4: Tích Phân\n∫ f(x)dx = F(x) + C",
        summary="Ảnh bảng đen giảng đường với công thức tích phân.",
        category="study",
        subject="math",
        source="seed",
        size_bytes=3400000,
    ),
    MediaRecord(
        file_id="seed-lecture-audio",
        filename="AUD_20260812_090000.mp3",
        s3_key="uploads/seed-lecture-audio.mp3",
        media_type="audio",
        content_type="audio/mpeg",
        status="READY",
        labels=["Speech", "Lecture"],
        transcript="Các em chú ý. Câu 3 đề thi cuối kỳ sẽ ra Thuật toán Round Robin và Virtual Memory. Nhớ ôn Page Fault rate.",
        summary="Ghi âm bài giảng hệ điều hành, thầy dặn đề thi cuối kỳ.",
        category="study",
        subject="os",
        source="seed",
        size_bytes=18200000,
    ),
    MediaRecord(
        file_id="seed-aws-slide",
        filename="IMG_20260813_142010.jpg",
        s3_key="uploads/seed-aws-slide.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        labels=["Text", "Document", "Electronics"],
        ocr_text="AWS Cloud Architecture\nServerless: S3 Event -> Lambda -> DynamoDB",
        summary="Slide bài giảng kiến trúc serverless AWS.",
        category="study",
        subject="cloud",
        source="seed",
        size_bytes=2800000,
    ),
    MediaRecord(
        file_id="seed-photo-receipt",
        filename="SCAN_20260814_115502.jpg",
        s3_key="uploads/seed-photo-receipt.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        labels=["Paper", "Text", "Document"],
        ocr_text="TIỆM PHOTO SINH VIÊN KHTN\nIn đề cương Mạng Máy Tính 45 trang - 22.500đ",
        summary="Hóa đơn photocopy tài liệu học tập.",
        category="receipts",
        source="seed",
        size_bytes=1900000,
    ),
    MediaRecord(
        file_id="seed-golden-dog",
        filename="IMG_20260810_152018.jpg",
        s3_key="uploads/seed-golden-dog.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        labels=["Dog", "Pet", "Grass", "Animal"],
        summary="Chó Golden Retriever trên thảm cỏ.",
        category="pets",
        source="seed",
        size_bytes=4100000,
    ),
    MediaRecord(
        file_id="seed-english-ielts",
        filename="IMG_20260811_101122.jpg",
        s3_key="uploads/seed-english-ielts.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        labels=["Text", "Document", "Paper"],
        ocr_text="Tiếng Anh chuyên ngành - IELTS Reading\nPassage 2: Climate change vocabulary",
        summary="Slide Tiếng Anh IELTS, môn ngoài ngành CNTT.",
        category="study",
        subject="english",
        source="seed",
        size_bytes=2100000,
    ),
]


class StubVision:
    def analyze_image(self, object_key: str, filename: str = "") -> tuple[list[str], str]:
        name = f"{object_key} {filename}".lower()
        if any(token in name for token in ("dog", "cat", "pet", "cho", "meo")):
            return ["Dog", "Pet", "Animal"], ""
        if any(token in name for token in ("receipt", "invoice", "bill", "hoa-don")):
            return ["Paper", "Text", "Document"], "Hóa đơn VAT 100000 VND"
        if any(token in name for token in ("slide", "board", "aws", "lecture")):
            return ["Text", "Document", "Whiteboard"], "AWS Lambda DynamoDB"
        return ["Object"], ""


class StubSpeech:
    def start_job(self, object_key: str, media_format: str, file_id: str = "") -> str:
        safe_name = re.sub(r"[^0-9a-zA-Z._-]", "_", object_key.replace("/", "-"))
        safe_fid = re.sub(r"[^0-9a-zA-Z._-]", "_", file_id) if file_id else ""
        if safe_fid:
            return f"agentsys--{safe_fid}--{safe_name}"[:200]
        return f"agentsys-{safe_name}"[:200]

    def wait_for_job(self, job_name: str) -> str:
        return "Các em chú ý. Câu 3 đề thi cuối kỳ sẽ ra Thuật toán Round Robin."

    def read_job_transcript(self, job_name: str) -> str:
        return self.wait_for_job(job_name)

    def transcribe(self, object_key: str, media_format: str, file_id: str = "") -> str:
        return self.wait_for_job(f"job-{file_id or object_key}")


class StubPlanner:
    client = None

    def plan(self, user_query: str) -> SearchPlan:
        import time
        from apps.aws.aws_services import _PLAN_CACHE, _PLAN_CACHE_TTL_SECONDS
        cache_key = " ".join(user_query.strip().lower().split())
        now = time.time()
        if cache_key and cache_key in _PLAN_CACHE:
            cached_at, cached_plan = _PLAN_CACHE[cache_key]
            if now - cached_at < _PLAN_CACHE_TTL_SECONDS:
                return cached_plan.model_copy(deep=True)

        query = user_query.lower()
        keywords = [token for token in re.findall(r"[\wÀ-ỹ]+", user_query) if len(token) > 2]
        media_type = None
        category = None
        if any(token in query for token in ("audio", "ghi âm", "mp3", "nói", "thầy")):
            media_type = "audio"
        elif any(token in query for token in ("video", "clip", "mp4")):
            media_type = "video"
        elif any(token in query for token in ("ảnh", "hình", "jpg")):
            media_type = "image"
        if any(token in query.split() for token in ("chó", "mèo", "thú", "cho")):
            category = "pets"
        elif any(token in query for token in ("hóa đơn", "biên lai")):
            category = "receipts"
        subject = infer_subject([], user_query, "", "")
        if subject == "none":
            subject = None
        elif category is None:
            category = "study"
        plan = SearchPlan(
            keywords=keywords[:8],
            media_type=media_type,
            category=category,
            subject=subject,
            rationale="pytest stub planner — production uses Amazon Bedrock",
            planner_source="bedrock",
        )
        if cache_key:
            _PLAN_CACHE[cache_key] = (now, plan.model_copy(deep=True))
        return plan


# Aliases for backwards compatibility
FakeVision = StubVision
FakeSpeech = StubSpeech
FakePlanner = StubPlanner


def setup_moto_infra() -> None:
    """Create S3 bucket and DynamoDB table in Moto emulator."""
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    try:
        s3.head_bucket(Bucket=settings.MEDIA_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=settings.MEDIA_BUCKET)

    dynamo = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    try:
        table = dynamo.Table(settings.METADATA_TABLE)
        table.load()
    except Exception:
        dynamo.create_table(
            TableName=settings.METADATA_TABLE,
            KeySchema=[{"AttributeName": "file_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "file_id", "AttributeType": "S"},
                {"AttributeName": "category", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "category-index",
                    "KeySchema": [{"AttributeName": "category", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )


def seed_moto_catalog() -> None:
    """Seed initial records into real DynamoDB table running in Moto."""
    catalog = DynamoCatalog()
    for record in SAMPLE_RECORDS:
        catalog.put(record)


def build_test_runtime() -> Runtime:
    """Build a Runtime where storage, catalog, and metrics use real AWS SDK with Moto."""
    return Runtime(
        catalog=DynamoCatalog(),
        store=S3ObjectStore(),
        vision=StubVision(),
        speech=StubSpeech(),
        planner=StubPlanner(),
        metrics=CloudWatchMetrics(),
        provider="aws",
    )


# Alias
build_fake_runtime = build_test_runtime
