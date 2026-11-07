"""Tests for edge cases, null-safety, and type coercion identified during pure code audit."""
from decimal import Decimal
from io import BytesIO
import pytest
from PIL import Image

from apps.aws.providers import get_runtime
from apps.aws.image_convert import image_bytes_to_jpeg, make_thumbnail_jpeg
from apps.classify.engine import infer_category, infer_subject, _nearest
from apps.domain import MediaRecord, record_haystack
from apps.search.vector_engine import cosine_similarity


def test_media_record_null_coercion():
    raw_data = {
        "file_id": "test_null_123",
        "filename": "document.png",
        "s3_key": "uploads/test_null_123.png",
        "media_type": "image",
        "content_type": "image/png",
        "status": "READY",
        "ocr_text": None,
        "transcript": None,
        "summary": None,
        "subject": None,
        "labels": None,
        "size_bytes": None,
    }
    record = MediaRecord.model_validate(raw_data)
    assert record.ocr_text == ""
    assert record.transcript == ""
    assert record.summary == ""
    assert record.subject == "none"
    assert record.labels == []
    assert record.size_bytes == 0


def test_record_haystack_with_null_attributes():
    record = MediaRecord(
        file_id="test_haystack",
        filename="notes.pdf",
        s3_key="uploads/notes.pdf",
        media_type="other",
        content_type="application/pdf",
        status="READY",
    )
    haystack = record_haystack(record)
    assert isinstance(haystack, str)
    assert "notes.pdf" in haystack


def test_cosine_similarity_with_decimal_and_edge_cases():
    # Mixed Decimal and float
    vec_a = [Decimal("0.6"), Decimal("0.8")]
    vec_b = [0.6, 0.8]
    sim = cosine_similarity(vec_a, vec_b)
    assert pytest.approx(sim, 0.0001) == 1.0

    # Orthogonal vectors
    sim_ortho = cosine_similarity([Decimal("1.0"), Decimal("0.0")], [0.0, 1.0])
    assert pytest.approx(sim_ortho, 0.0001) == 0.0

    # Mismatched lengths
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    # Empty vectors
    assert cosine_similarity([], []) == 0.0

    # Zero norm vectors
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_classify_infer_category_and_subject_none_safety():
    # Calling infer_category with None labels and None text
    cat = infer_category("image", None, None)
    assert cat in {"other", "scenes", "receipts", "pets", "people", "food", "study"}

    # Calling infer_subject with None values
    subj = infer_subject(None, None, None, None)
    assert subj == "none"

    # Calling _nearest with None
    res, score = _nearest(None, {})
    assert res is None
    assert score == 0.0


def test_raw_transcript_endpoint_s3_fallback(client, auth_headers, monkeypatch):
    runtime = get_runtime()
    record = MediaRecord(
        file_id="audit_transcript_fallback",
        filename="lecture.mp3",
        s3_key="uploads/lecture.mp3",
        media_type="audio",
        content_type="audio/mp3",
        status="READY",
        transcript="Bài giảng Giải tích 1 chương giới hạn dãy số.",
    )
    runtime.catalog.put(record)

    # Simulate S3 NoSuchKey or client exception when fetching raw transcript
    def broken_get_bytes(key):
        raise RuntimeError("Simulated S3 network failure")

    monkeypatch.setattr(runtime.store, "get_bytes", broken_get_bytes)

    resp = client.get(f"/api/v1/media/items/{record.file_id}/transcript-raw", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_id"] == record.file_id
    assert "Bài giảng Giải tích 1" in data["transcript"]


def test_image_convert_deterministic_cleanup():
    # Create a small valid in-memory PNG
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    jpeg = image_bytes_to_jpeg(raw_bytes)
    assert len(jpeg) > 0
    assert jpeg.startswith(b"\xff\xd8")  # JPEG magic bytes

    thumb = make_thumbnail_jpeg(raw_bytes, max_edge=50)
    assert len(thumb) > 0
    assert thumb.startswith(b"\xff\xd8")
