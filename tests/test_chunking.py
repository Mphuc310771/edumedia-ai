import json
import pytest

from pipeline.chunking import TranscriptChunk, chunk_transcribe_json


def make_mock_transcribe_payload(total_words: int, words_per_sec: float = 2.0, sentence_len: int = 10):
    """Generate mock Transcribe payload with timestamps and periodic punctuation."""
    items = []
    current_time = 0.0
    for i in range(total_words):
        start = current_time
        end = start + (1.0 / words_per_sec)
        current_time = end

        items.append({
            "start_time": f"{start:.2f}",
            "end_time": f"{end:.2f}",
            "type": "pronunciation",
            "alternatives": [{"content": f"word{i}"}],
        })

        if (i + 1) % sentence_len == 0:
            items.append({
                "type": "punctuation",
                "alternatives": [{"content": "."}],
            })
            current_time += 0.5  # brief pause

    return {
        "results": {
            "transcripts": [{"transcript": "mock transcript text"}],
            "items": items,
        }
    }


def test_chunking_empty_payload():
    chunks = chunk_transcribe_json({}, "file-123")
    assert chunks == []


def test_chunking_fallback_raw_text_only():
    payload = {
        "results": {
            "transcripts": [{"transcript": "Đây là bài giảng về hệ điều hành."}],
            "items": [],
        }
    }
    chunks = chunk_transcribe_json(payload, "file-123")
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "file-123-chunk-0000"
    assert chunks[0].text == "Đây là bài giảng về hệ điều hành."


def test_chunking_short_audio_single_chunk():
    # 200 words at 2 words/sec = 100 seconds (< 300s min target)
    payload = make_mock_transcribe_payload(total_words=200, words_per_sec=2.0)
    chunks = chunk_transcribe_json(payload, "file-short", target_min_seconds=300.0, target_max_seconds=600.0)

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].chunk_id == "file-short-chunk-0000"
    assert chunks[0].start_time == 0.0
    assert chunks[0].end_time > 90.0


def test_chunking_long_audio_splits_at_sentence_boundaries():
    # 1800 words at 2 words/sec = 900 seconds (15 minutes)
    payload = make_mock_transcribe_payload(total_words=1800, words_per_sec=2.0, sentence_len=12)
    chunks = chunk_transcribe_json(
        payload,
        "file-long",
        target_min_seconds=300.0,
        target_max_seconds=600.0,
    )

    assert len(chunks) >= 2
    # Ensure sequential chronological indexes
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.chunk_id == f"file-long-chunk-{i:04d}"
        # Ensure sentence boundary (ends with period)
        assert c.text.endswith(".")


def test_chunking_silence_gap_split():
    # Construct words with an explicit 3.0s silence gap
    items = [
        {"start_time": "0.0", "end_time": "1.0", "type": "pronunciation", "alternatives": [{"content": "Chào"}]},
        {"start_time": "1.0", "end_time": "2.0", "type": "pronunciation", "alternatives": [{"content": "lớp"}]},
        # 3.0s silence break here
        {"start_time": "5.0", "end_time": "6.0", "type": "pronunciation", "alternatives": [{"content": "Hôm"}]},
        {"start_time": "6.0", "end_time": "7.0", "type": "pronunciation", "alternatives": [{"content": "nay"}]},
        {"type": "punctuation", "alternatives": [{"content": "."}]},
    ]
    payload = {"results": {"items": items}}
    chunks = chunk_transcribe_json(payload, "file-gap", target_min_seconds=3.0, target_max_seconds=10.0, silence_break_seconds=1.5)

    assert len(chunks) >= 1
    assert "Chào lớp" in chunks[0].text
