from __future__ import annotations

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

_EASYOCR_READER = None


def get_easyocr_reader():
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        try:
            import easyocr
            import torch

            gpu_available = torch.cuda.is_available()
            logger.info("Khởi tạo EasyOCR Engine (CUDA GPU khả dụng: %s)...", gpu_available)
            _EASYOCR_READER = easyocr.Reader(["vi", "en"], gpu=gpu_available)
        except Exception as exc:
            logger.warning("Không thể khởi tạo EasyOCR GPU: %s. Sẽ dùng Heuristic fallback.", exc)
            _EASYOCR_READER = False
    return _EASYOCR_READER if _EASYOCR_READER is not False else None


class LocalGPUVision:
    """Real Local OCR Vision Analyzer powered by NVIDIA RTX GPU (EasyOCR CUDA)."""

    def __init__(self, fallback_vision=None):
        self.fallback = fallback_vision

    def analyze_image(self, object_key: str, filename: str = "") -> Tuple[List[str], str]:
        from apps.aws.providers import get_runtime

        runtime = get_runtime()
        reader = get_easyocr_reader()

        if reader is None:
            if self.fallback:
                return self.fallback.analyze_image(object_key, filename)
            return ["Image"], ""

        try:
            # Lấy bytes của ảnh từ bộ nhớ in-memory object store
            img_data = runtime.store.get_object(object_key)
            if not img_data:
                if self.fallback:
                    return self.fallback.analyze_image(object_key, filename)
                return ["Image"], ""

            body, _ = img_data
            # Chạy nhận diện chữ OCR trực tiếp trên GPU RTX bằng EasyOCR
            results = reader.readtext(body)
            # results format: [ (bbox, text, prob), ... ]
            lines = [res[1].strip() for res in results if res[2] >= 0.2 and res[1].strip()]
            ocr_text = "\n".join(lines)

            # Gán nhãn thông minh dựa trên chính nội dung văn bản OCR trích xuất được
            labels = ["Photo", "Document"] if ocr_text else ["Photo"]
            text_lower = ocr_text.lower()
            if any(k in text_lower for k in ("toán", "đạo hàm", "tích phân", "formula", "chương", "bài tập", "giải tích")):
                labels.extend(["Math", "Lecture", "Whiteboard"])
            elif any(k in text_lower for k in ("hóa đơn", "vat", "phiếu thu", "vnđ", "tiền", "thanh toán", "cộng")):
                labels.extend(["Invoice", "Receipt", "Bill"])
            elif any(k in text_lower for k in ("aws", "cloud", "architecture", "serverless", "lambda", "s3", "dynamodb")):
                labels.extend(["Cloud", "Architecture", "AWS"])
            elif any(k in text_lower for k in ("menu", "cà phê", "trà", "coffee", "món", "thực đơn")):
                labels.extend(["Food", "Menu", "Drink"])

            logger.info("Local GPU OCR thành công trên %s: bóc được %d dòng chữ qua RTX GPU", object_key, len(lines))
            return labels, ocr_text
        except Exception as exc:
            logger.warning("Local GPU OCR lỗi trên %s: %s. Sử dụng fallback.", object_key, exc)
            if self.fallback:
                return self.fallback.analyze_image(object_key, filename)
            return ["Image"], ""
