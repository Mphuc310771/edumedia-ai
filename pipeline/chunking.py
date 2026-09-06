"""Silence & Segment-Aware Chunking for Tier 2 Map-Reduce LLM Refinement.

Splits Amazon Transcribe JSON outputs into logical 5-10 minute chunks at natural
sentence boundaries and silence intervals, preventing mid-sentence truncation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default chunking parameters (in seconds)
DEFAULT_TARGET_MIN_SECONDS: float = 300.0  # 5 minutes
DEFAULT_TARGET_MAX_SECONDS: float = 600.0  # 10 minutes
DEFAULT_SILENCE_BREAK_SECONDS: float = 1.2  # Pause duration considered a sentence break


@dataclass
class TranscriptWord:
    content: str
    start_time: float
    end_time: float
    is_punctuation: bool = False


@dataclass
class TranscriptSentence:
    text: str
    start_time: float
    end_time: float
    word_count: int


@dataclass
class TranscriptChunk:
    chunk_id: str
    chunk_index: int
    file_id: str
    start_time: float
    end_time: float
    text: str
    item_count: int


def _parse_transcribe_items(transcribe_payload: Dict[str, Any]) -> List[TranscriptWord]:
    """Parse raw Amazon Transcribe results.items into structured TranscriptWord items."""
    results = transcribe_payload.get("results", {})
    raw_items = results.get("items", [])
    if not raw_items:
        return []

    words: List[TranscriptWord] = []
    last_end = 0.0

    for item in raw_items:
        item_type = item.get("type", "pronunciation")
        alternatives = item.get("alternatives", [{}])
        content = alternatives[0].get("content", "") if alternatives else ""

        if not content:
            continue

        if item_type == "punctuation":
            # Punctuation attaches to the preceding word's end time
            words.append(
                TranscriptWord(
                    content=content,
                    start_time=last_end,
                    end_time=last_end,
                    is_punctuation=True,
                )
            )
        else:
            try:
                start_time = float(item.get("start_time", last_end))
                end_time = float(item.get("end_time", start_time))
            except (ValueError, TypeError):
                start_time = last_end
                end_time = last_end

            last_end = end_time
            words.append(
                TranscriptWord(
                    content=content,
                    start_time=start_time,
                    end_time=end_time,
                    is_punctuation=False,
                )
            )

    return words


def _group_into_sentences(
    words: List[TranscriptWord],
    silence_break_seconds: float = DEFAULT_SILENCE_BREAK_SECONDS,
) -> List[TranscriptSentence]:
    """Group sequential words into coherent sentences using punctuation and silence intervals."""
    if not words:
        return []

    sentences: List[TranscriptSentence] = []
    current_tokens: List[str] = []
    sentence_start = words[0].start_time
    sentence_end = words[0].end_time
    word_count = 0

    for i, w in enumerate(words):
        if w.is_punctuation:
            # Attach punctuation directly to previous token without leading space
            if current_tokens:
                current_tokens[-1] = f"{current_tokens[-1]}{w.content}"
            else:
                current_tokens.append(w.content)

            # End sentence on strong punctuation: . ? !
            if w.content in {".", "?", "!"}:
                sentence_text = " ".join(current_tokens).strip()
                if sentence_text:
                    sentences.append(
                        TranscriptSentence(
                            text=sentence_text,
                            start_time=sentence_start,
                            end_time=sentence_end,
                            word_count=word_count,
                        )
                    )
                current_tokens = []
                word_count = 0
                if i + 1 < len(words):
                    sentence_start = words[i + 1].start_time
        else:
            # Check for significant silence gap between previous word and current word
            if i > 0 and not words[i - 1].is_punctuation:
                silence_gap = w.start_time - words[i - 1].end_time
                if silence_gap >= silence_break_seconds and current_tokens:
                    # Natural speech pause break
                    sentence_text = " ".join(current_tokens).strip()
                    if sentence_text:
                        sentences.append(
                            TranscriptSentence(
                                text=sentence_text,
                                start_time=sentence_start,
                                end_time=words[i - 1].end_time,
                                word_count=word_count,
                            )
                        )
                    current_tokens = []
                    word_count = 0
                    sentence_start = w.start_time

            current_tokens.append(w.content)
            sentence_end = w.end_time
            word_count += 1

    # Flush any remaining tokens
    if current_tokens:
        sentence_text = " ".join(current_tokens).strip()
        if sentence_text:
            sentences.append(
                TranscriptSentence(
                    text=sentence_text,
                    start_time=sentence_start,
                    end_time=sentence_end,
                    word_count=word_count,
                )
            )

    return sentences


def chunk_transcribe_json(
    transcribe_payload: Dict[str, Any],
    file_id: str,
    target_min_seconds: float = DEFAULT_TARGET_MIN_SECONDS,
    target_max_seconds: float = DEFAULT_TARGET_MAX_SECONDS,
    silence_break_seconds: float = DEFAULT_SILENCE_BREAK_SECONDS,
) -> List[TranscriptChunk]:
    """Chunk Amazon Transcribe JSON payload into segment-aware chunks for LLM Map-Reduce.

    Args:
        transcribe_payload: Parsed JSON dict from Amazon Transcribe.
        file_id: Unique file identifier.
        target_min_seconds: Minimum target duration before attempting a sentence break.
        target_max_seconds: Maximum ceiling duration for a chunk.
        silence_break_seconds: Silence duration threshold for pause-based sentence splitting.

    Returns:
        List of TranscriptChunk items with deterministic chunk_id and chronological chunk_index.
    """
    words = _parse_transcribe_items(transcribe_payload)
    if not words:
        # Fallback if raw text is provided without items
        results = transcribe_payload.get("results", {})
        transcripts = results.get("transcripts", [])
        raw_text = transcripts[0].get("transcript", "").strip() if transcripts else ""
        if not raw_text:
            return []
        return [
            TranscriptChunk(
                chunk_id=f"{file_id}-chunk-0000",
                chunk_index=0,
                file_id=file_id,
                start_time=0.0,
                end_time=0.0,
                text=raw_text,
                item_count=len(raw_text.split()),
            )
        ]

    sentences = _group_into_sentences(words, silence_break_seconds=silence_break_seconds)
    if not sentences:
        return []

    total_duration = sentences[-1].end_time - sentences[0].start_time

    # Short audio optimization: if entire audio fits within target_max_seconds, single chunk
    if total_duration <= target_max_seconds:
        combined_text = " ".join(s.text for s in sentences)
        return [
            TranscriptChunk(
                chunk_id=f"{file_id}-chunk-0000",
                chunk_index=0,
                file_id=file_id,
                start_time=sentences[0].start_time,
                end_time=sentences[-1].end_time,
                text=combined_text,
                item_count=sum(s.word_count for s in sentences),
            )
        ]

    chunks: List[TranscriptChunk] = []
    current_chunk_sentences: List[TranscriptSentence] = []
    chunk_start_time = sentences[0].start_time

    for s in sentences:
        current_chunk_sentences.append(s)
        current_duration = s.end_time - chunk_start_time

        # Check if we should finalize the current chunk
        if current_duration >= target_min_seconds:
            # We reached minimum target duration; check if we should break now or at max ceiling
            if current_duration >= target_max_seconds or s.text.endswith((".", "!", "?")):
                chunk_text = " ".join(item.text for item in current_chunk_sentences)
                chunk_index = len(chunks)
                chunk = TranscriptChunk(
                    chunk_id=f"{file_id}-chunk-{chunk_index:04d}",
                    chunk_index=chunk_index,
                    file_id=file_id,
                    start_time=chunk_start_time,
                    end_time=s.end_time,
                    text=chunk_text,
                    item_count=sum(item.word_count for item in current_chunk_sentences),
                )
                chunks.append(chunk)
                current_chunk_sentences = []
                chunk_start_time = s.end_time

    # Flush any remaining sentences into the last chunk
    if current_chunk_sentences:
        chunk_text = " ".join(item.text for item in current_chunk_sentences)
        chunk_index = len(chunks)
        # If the remaining segment is very short and we already have a previous chunk, merge it
        if chunks and (current_chunk_sentences[-1].end_time - chunk_start_time) < (target_min_seconds * 0.3):
            last_chunk = chunks[-1]
            last_chunk.text = f"{last_chunk.text} {chunk_text}".strip()
            last_chunk.end_time = current_chunk_sentences[-1].end_time
            last_chunk.item_count += sum(item.word_count for item in current_chunk_sentences)
        else:
            chunk = TranscriptChunk(
                chunk_id=f"{file_id}-chunk-{chunk_index:04d}",
                chunk_index=chunk_index,
                file_id=file_id,
                start_time=chunk_start_time,
                end_time=current_chunk_sentences[-1].end_time,
                text=chunk_text,
                item_count=sum(item.word_count for item in current_chunk_sentences),
            )
            chunks.append(chunk)

    return chunks
