from __future__ import annotations

import logging
import os
import re
from typing import Optional

from apps.aws.providers import get_runtime
from apps.domain import CATEGORY_LABELS, MediaRecord, infer_category, infer_media_type

logger = logging.getLogger(__name__)

IMAGE_FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}
AUDIO_FORMATS = {".mp3": "mp3", ".wav": "wav", ".m4a": "mp4", ".flac": "flac"}
VIDEO_FORMATS = {".mp4": "mp4", ".mov": "mp4"}

LABEL_TRANSLATIONS = {
    # Technology / Study
    "computer": "Máy tính",
    "laptop": "Laptop",
    "electronics": "Thiết bị điện tử",
    "pc": "PC",
    "monitor": "Màn hình",
    "screen": "Màn hình hiển thị",
    "desk": "Bàn làm việc",
    "keyboard": "Bàn phím",
    "computer hardware": "Phần cứng",
    "hardware": "Thiết bị",
    "shelf": "Kệ sách",
    "bookcase": "Giá sách",
    "book": "Sách vở",
    "furniture": "Nội thất",
    "table": "Bàn",
    "study": "Học tập",
    # People
    "person": "Con người",
    "human": "Con người",
    "people": "Mọi người",
    "face": "Khuôn mặt",
    "head": "Khuôn mặt",
    "portrait": "Chân dung",
    "adult": "Người lớn",
    "male": "Nam giới",
    "female": "Nữ giới",
    "athlete": "Vận động viên",
    "player": "Cầu thủ",
    "soccer": "Bóng đá",
    "team": "Đội nhóm",
    "crowd": "Đám đông",
    # Animals / Pets
    "animal": "Động vật",
    "pet": "Thú cưng",
    "dog": "Chó",
    "cat": "Mèo",
    "mammal": "Động vật có vú",
    "tiger": "Hổ",
    "lion": "Sư tử",
    "bird": "Chim",
    "fish": "Cá",
    "wildlife": "Động vật hoang dã",
    # Nature / Scenes
    "nature": "Thiên nhiên",
    "landscape": "Cảnh quan",
    "plant": "Cây cối",
    "tree": "Cây xanh",
    "vegetation": "Thảm thực vật",
    "land": "Cảnh vật",
    "outdoors": "Ngoài trời",
    "beach": "Bãi biển",
    "mountain": "Núi non",
    "sunset": "Hoàng hôn",
    "sunrise": "Bình minh",
    "sky": "Bầu trời",
    "cloud": "Mây trời",
    "sea": "Biển cả",
    "water": "Mặt nước",
    "building": "Tòa nhà",
    "city": "Đô thị",
    "street": "Đường phố",
    "road": "Đường đi",
    "intersection": "Ngã tư",
    "flower": "Hoa tươi",
    "flower arrangement": "Bình hoa",
    "transportation": "Phương tiện",
    "vehicle": "Xe cộ",
    "car": "Ô tô",
    "boat": "Thuyền bè",
    # Food / Drink
    "food": "Món ăn",
    "meal": "Bữa ăn",
    "dish": "Đĩa ăn",
    "lunch": "Bữa ăn",
    "dinner": "Bữa ăn",
    "drink": "Đồ uống",
    "beverage": "Nước uống",
    "coffee": "Cà phê",
    "tea": "Trà",
    "restaurant": "Nhà hàng",
    "cafeteria": "Quán ăn",
    "indoors": "Trong phòng",
    # Receipts / Documents
    "receipt": "Hóa đơn",
    "invoice": "Biên lai",
    "whiteboard": "Bảng viết",
    "document": "Tài liệu",
    "paper": "Giấy tờ",
    "text": "Văn bản",
    # Audio / Video
    "speech": "Giọng nói",
    "audio": "Ghi âm",
    "video": "Video",
    "music": "Âm thanh",
}


def translate_labels(labels: list[str]) -> list[str]:
    """Translate raw Rekognition English labels to clean, natural Vietnamese tags."""
    seen = set()
    vietnamese_tags = []
    for l in labels:
        clean_key = l.lower().strip()
        trans = LABEL_TRANSLATIONS.get(clean_key, l.capitalize())
        # Filter out noisy tags
        if trans.lower() in {"accessories", "bag", "handbag", "clothing", "apparel"}:
            continue
        if trans not in seen:
            seen.add(trans)
            vietnamese_tags.append(trans)
    return vietnamese_tags[:6]


def _clean_ocr_snippet(ocr_text: str) -> str:
    """Extract a clean, readable text snippet from OCR, filtering out noisy symbols."""
    lines = [line.strip() for line in (ocr_text or "").splitlines() if line.strip()]
    meaningful = [l for l in lines if not l.startswith("http") and len(l) > 2 and not l.isdigit()]
    if meaningful:
        combined = " • ".join(meaningful[:3])
        return combined[:80]
    return ""


def ingest_object(file_id: str, object_key: str, filename: Optional[str] = None, content_type: str = "") -> MediaRecord:
    runtime = get_runtime()
    name = filename or os.path.basename(object_key)
    media_type = infer_media_type(name, content_type)
    record = MediaRecord(
        file_id=file_id,
        filename=name,
        s3_key=object_key,
        media_type=media_type,
        content_type=content_type or "application/octet-stream",
        status="INDEXING",
        source="pipeline",
    )
    runtime.catalog.put(record)

    try:
        ext = os.path.splitext(name)[1].lower()
        labels: list[str] = []
        ocr = ""
        transcript = ""

        if media_type == "image":
            try:
                labels, ocr = runtime.vision.analyze_image(object_key, name)
            except Exception as exc:
                logger.warning("Vision analysis error on %s: %s", name, exc)
                labels = ["Ảnh"]
                ocr = ""
        elif media_type in {"audio", "video"}:
            try:
                media_format = {**AUDIO_FORMATS, **VIDEO_FORMATS}.get(ext, "mp4")
                transcript = runtime.speech.transcribe(object_key, media_format)
                labels = ["Giọng nói", "Ghi âm"] if transcript else ["Phương tiện"]
            except Exception as exc:
                logger.warning("Speech analysis error on %s: %s", name, exc)
                labels = ["Ghi âm"]
        else:
            labels = ["Tài liệu"]

        blob = " ".join([*labels, ocr, transcript, name])
        record.category = infer_category(media_type, labels, blob)
        record.labels = translate_labels(labels)
        record.ocr_text = ocr
        record.transcript = transcript
        record.summary = _build_summary(record)
        record.status = "READY"
        record.error = None
        runtime.catalog.put(record)
        runtime.metrics.emit("MediaIngested", 1)
        return record
    except Exception as exc:
        logger.exception("ingest_failed file_id=%s", file_id)
        record.status = "FAILED"
        record.error = str(exc)
        runtime.catalog.put(record)
        runtime.metrics.emit("MediaIngestFailed", 1)
        raise


def _build_summary(record: MediaRecord) -> str:
    category_name = CATEGORY_LABELS.get(record.category, record.category)

    if record.media_type == "audio":
        if record.transcript and not record.transcript.startswith("Bản ghi"):
            clean_first = record.transcript.strip()[:100].rstrip(".")
            return f"Bản ghi âm lời thoại: \"{clean_first}...\""
        return f"File ghi âm đã lưu trữ và lập chỉ mục trong danh mục {category_name}."

    if record.media_type == "video":
        return f"Tệp video đa phương tiện được lưu trữ trong danh mục {category_name}."

    # Image summary synthesis
    labels_str = ", ".join(record.labels[:4]) if record.labels else ""
    ocr_snippet = _clean_ocr_snippet(record.ocr_text)

    if labels_str and ocr_snippet:
        return f"Ảnh chụp gồm {labels_str.lower()}. Văn bản hiển thị: \"{ocr_snippet}\"."
    if labels_str:
        return f"Ảnh chụp nhận diện {labels_str.lower()}, xếp vào danh mục {category_name}."
    if ocr_snippet:
        return f"Văn bản trích xuất: \"{ocr_snippet}\"."

    return f"Tài liệu {record.filename} đã được phân loại vào danh mục {category_name}."
