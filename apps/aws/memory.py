from __future__ import annotations

import re
import threading
from typing import Dict, List, Optional
from urllib.parse import quote

from apps.domain import MediaRecord, SearchPlan, fold_text, record_haystack


_LOCK = threading.Lock()
_CATALOG: Dict[str, MediaRecord] = {}
_OBJECTS: Dict[str, tuple[bytes, str]] = {}


SEED_RECORDS = [
    MediaRecord(
        file_id="seed-lecture-board",
        filename="IMG_20260812_091522.jpg",
        s3_key="uploads/seed-lecture-board.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        labels=["Text", "Whiteboard", "Classroom", "Person"],
        ocr_text="Toán Cao Cấp - Chương 4: Tích Phân\n∫ f(x)dx = F(x) + C\nNộp bài tập nhóm trước 23h59 Chủ Nhật.",
        summary="Ảnh bảng đen giảng đường với công thức tích phân.",
        category="study",
        preview_url="https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800&q=80",
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
        ocr_text="AWS Cloud Architecture\nServerless: S3 Event -> Lambda -> DynamoDB\nAmazon Rekognition + Amazon Transcribe",
        summary="Slide bài giảng kiến trúc serverless AWS.",
        category="study",
        preview_url="https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80",
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
        ocr_text="TIỆM PHOTO SINH VIÊN KHTN\nIn đề cương Mạng Máy Tính 45 trang - 22.500đ\nTổng cộng: 30.500 VNĐ",
        summary="Hóa đơn photocopy tài liệu học tập.",
        category="receipts",
        preview_url="https://images.unsplash.com/photo-1586281380349-632531db7ed4?w=800&q=80",
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
        preview_url="https://images.unsplash.com/photo-1552053831-71594a27632d?w=800&q=80",
        source="seed",
        size_bytes=4100000,
    ),
    MediaRecord(
        file_id="seed-coffee",
        filename="IMG_20260813_074512.jpg",
        s3_key="uploads/seed-coffee.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        labels=["Cup", "Coffee", "Food", "Table"],
        summary="Tách cà phê latte trên bàn gỗ.",
        category="food",
        preview_url="https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&q=80",
        source="seed",
        size_bytes=3100000,
    ),
    MediaRecord(
        file_id="seed-beach",
        filename="IMG_20260808_174500.jpg",
        s3_key="uploads/seed-beach.jpg",
        media_type="image",
        content_type="image/jpeg",
        status="READY",
        labels=["Beach", "Ocean", "Sunset", "Outdoor"],
        summary="Hoàng hôn trên bãi biển.",
        category="scenes",
        preview_url="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80",
        source="seed",
        size_bytes=6100000,
    ),
    MediaRecord(
        file_id="seed-campus-video",
        filename="VID_20260814_172015.mp4",
        s3_key="uploads/seed-campus-video.mp4",
        media_type="video",
        content_type="video/mp4",
        status="READY",
        labels=["Person", "Speech"],
        transcript="Nhóm em xin trình bày đồ án AgentSys trên Amazon S3, Lambda và Amazon Bedrock.",
        summary="Video thuyết trình đồ án trên hội trường.",
        category="videos",
        preview_url="https://images.unsplash.com/photo-1475721027785-f74eccf877e2?w=800&q=80",
        source="seed",
        size_bytes=38500000,
    ),
]


class MemoryCatalog:
    def __init__(self, seed: bool = True):
        if seed:
            self.ensure_seed()

    def ensure_seed(self) -> None:
        with _LOCK:
            if _CATALOG:
                return
            for record in SEED_RECORDS:
                _CATALOG[record.file_id] = record.model_copy(deep=True)

    def put(self, record: MediaRecord) -> None:
        with _LOCK:
            _CATALOG[record.file_id] = record

    def get(self, file_id: str) -> Optional[MediaRecord]:
        with _LOCK:
            record = _CATALOG.get(file_id)
            return record.model_copy(deep=True) if record else None

    def list_all(self) -> List[MediaRecord]:
        with _LOCK:
            return [item.model_copy(deep=True) for item in _CATALOG.values()]

    def search(self, plan: SearchPlan) -> List[MediaRecord]:
        items = self.list_all()
        if plan.media_type:
            items = [item for item in items if item.media_type == plan.media_type]
        if plan.category:
            items = [item for item in items if item.category == plan.category]
        if not plan.keywords:
            return items
        scored = []
        for item in items:
            haystack = record_haystack(item)
            hits = sum(1 for kw in plan.keywords if fold_text(kw) in haystack)
            if hits:
                scored.append((hits, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored]

    def delete(self, file_id: str) -> bool:
        with _LOCK:
            return bool(_CATALOG.pop(file_id, None))

    def clear(self) -> None:
        with _LOCK:
            _CATALOG.clear()
            _OBJECTS.clear()


class MemoryObjectStore:
    def presign_put(self, object_key: str, content_type: str, expires: int = 3600) -> str:
        return f"/api/v1/media/local-upload/{quote(object_key, safe='')}?content_type={quote(content_type)}&exp={expires}"

    def presign_get(self, object_key: str, expires: int = 3600) -> str:
        return f"/api/v1/media/local-object/{quote(object_key, safe='')}?exp={expires}"

    def get_bytes(self, object_key: str) -> bytes:
        body, _ = _OBJECTS.get(object_key, (b"", "application/octet-stream"))
        return body

    def put_bytes(self, object_key: str, body: bytes, content_type: str) -> None:
        _OBJECTS[object_key] = (body, content_type)

    def object_uri(self, object_key: str) -> str:
        return f"memory://{object_key}"

    def get_object(self, object_key: str) -> Optional[tuple[bytes, str]]:
        return _OBJECTS.get(object_key)


class MemoryVision:
    def analyze_image(self, object_key: str, filename: str = "") -> tuple[list[str], str]:
        name = f"{object_key} {filename}".lower()
        labels = ["Object"]
        ocr = ""
        if any(token in name for token in ("dog", "cat", "pet", "cho", "meo")):
            labels = ["Dog", "Pet", "Animal"]
        elif any(token in name for token in ("receipt", "invoice", "bill", "hoa-don")):
            labels = ["Paper", "Text", "Document"]
            ocr = "LOCAL OCR PLACEHOLDER — enable Rekognition on AWS for real text."
        elif any(token in name for token in ("slide", "board", "aws", "lecture")):
            labels = ["Text", "Document", "Whiteboard"]
            ocr = "LOCAL OCR PLACEHOLDER — Amazon Rekognition DetectText on AWS."
        elif any(token in name for token in ("beach", "city", "sunset")):
            labels = ["Outdoor", "Landscape"]
        elif any(token in name for token in ("coffee", "food", "cup")):
            labels = ["Food", "Cup"]
        return labels, ocr


class MemorySpeech:
    def transcribe(self, object_key: str, media_format: str) -> str:
        return (
            f"[local transcript placeholder for {object_key} ({media_format}). "
            "Amazon Transcribe produces real Vietnamese speech-to-text on AWS.]"
        )


class MemoryPlanner:
    def plan(self, user_query: str) -> SearchPlan:
        query = user_query.lower()
        keywords = [token for token in re.findall(r"[\wÀ-ỹ]+", user_query) if len(token) > 2]
        media_type = None
        category = None
        if any(token in query for token in ("audio", "ghi âm", "mp3", "nói", "thầy")):
            media_type = "audio"
        elif any(token in query for token in ("video", "clip", "mp4")):
            media_type = "video"
        elif any(token in query for token in ("ảnh", "hình", "ảnh chụp", "jpg")):
            media_type = "image"
        if any(token in query for token in ("chó", "mèo", "thú")):
            category = "pets"
        elif any(token in query for token in ("hóa đơn", "biên lai", "tiền")):
            category = "receipts"
        elif any(token in query for token in ("biển", "hoàng hôn", "cảnh")):
            category = "scenes"
        elif any(token in query for token in ("cà phê", "đồ ăn", "giày")):
            category = "food"
        elif any(token in query for token in ("thi", "bảng", "tích phân", "aws", "bài giảng")):
            category = "study"
        return SearchPlan(
            keywords=keywords[:8],
            media_type=media_type,
            category=category,
            rationale="Heuristic planner used when Bedrock is not configured.",
        )


class MemoryMetrics:
    def emit(self, name: str, value: float, unit: str = "Count") -> None:
        return None


def reset_memory() -> None:
    with _LOCK:
        _CATALOG.clear()
        _OBJECTS.clear()
