"""Convert images Rekognition cannot read (WebP, GIF, BMP) into JPEG bytes."""
from __future__ import annotations

from io import BytesIO

REKOGNITION_OK_EXT = {".jpg", ".jpeg", ".png"}
CONVERT_EXT = {".webp", ".gif", ".bmp", ".tif", ".tiff"}
MAX_JPEG_BYTES = 4_500_000
MAX_EDGE = 4096


def needs_rekognition_convert(filename: str) -> bool:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in CONVERT_EXT


def image_bytes_to_jpeg(raw: bytes) -> bytes:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Cần cài Pillow để chuyển WebP/GIF sang JPEG cho Rekognition.") from exc

    with Image.open(BytesIO(raw)) as original:
        original.load()
        image = original.convert("RGB") if original.mode != "RGB" else original.copy()

    try:
        width, height = image.size
        longest = max(width, height)
        if longest > MAX_EDGE:
            scale = MAX_EDGE / float(longest)
            resized = image.resize((max(1, int(width * scale)), max(1, int(height * scale))))
            image.close()
            image = resized

        quality = 90
        jpeg = _save_jpeg(image, quality)
        while len(jpeg) > MAX_JPEG_BYTES and quality > 50:
            quality -= 10
            jpeg = _save_jpeg(image, quality)
        return jpeg
    finally:
        image.close()


def _save_jpeg(image, quality: int) -> bytes:
    out = BytesIO()
    image.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


def make_thumbnail_jpeg(raw: bytes, max_edge: int = 480) -> bytes:
    from PIL import Image

    with Image.open(BytesIO(raw)) as original:
        original.load()
        image = original.convert("RGB") if original.mode != "RGB" else original.copy()

    try:
        image.thumbnail((max_edge, max_edge))
        return _save_jpeg(image, 72)
    finally:
        image.close()
