"""Tier 1 Rule-Based Extraction & Fast Provisional Summarizer.

Executes synchronously in milliseconds immediately upon ASR completion.
Extracts announcements, topic overview, entity milestones, and calculates classification confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================

# Extended Vietnamese spoken fillers, hesitation markers, and conversational padding
VIETNAMESE_FILLERS: Set[str] = {
    # Single-word hesitation & discourse markers
    "à", "ạ", "ừ", "ừm", "ừừ", "ờ", "ờm", "ơ", "ơ kìa",
    "thì", "là", "mà", "cái", "kiểu", "đấy", "nhỉ", "nhé", "nè", "nghen", "hén",
    "vậy", "đó", "rồi", "nè", "kia", "hử", "ha",
    # Multi-word filler phrases
    "kiểu như", "kiểu là", "nói chung là", "thành ra là", "thực ra là", "nói thật là",
    "coi như là", "gọi là", "này nọ", "vân vân", "đúng không", "đúng hông",
    "hình dung không", "hình dung được không", "hiểu không", "hiểu hông",
    "tức là", "thế này thế kia", "như vậy", "đâu có sao", "thôi thì",
}

# Regex to detect consecutive word stutters common in speech and ASR transcripts
REPEATED_STUTTER_PATTERN = re.compile(
    r"\b([\wÀ-ỹ]+)\s+\1\b",
    re.IGNORECASE,
)

# Quality Filtering Thresholds
MIN_LINE_CHARS: int = 15
MIN_TOKEN_COUNT: int = 4
MAX_FILLER_DENSITY: float = 0.35
MAX_STUTTER_RATIO: float = 0.20

# Administrative / Announcement Regex Matchers
ADMIN_PRESENTATION_REGEX = re.compile(
    r"(?:trình bày|thuyết trình|báo cáo|demo|bảo vệ)\s*[:\-\—]?\s*([^\.\;\n]*?\d+\s*phút[^\.\;\n]*)",
    re.IGNORECASE,
)

ADMIN_EXAM_REGEX = re.compile(
    r"(?:thi lý thuyết|thi giữa kỳ|thi cuối kỳ|kỳ thi|lịch thi)\s*[:\-\—]?\s*([^\.\;\n]*?(?:ngày\s*)?\d+\s*(?:tháng|/)\s*\d+[^\.\;\n]*)",
    re.IGNORECASE,
)

ADMIN_SUBMISSION_REGEX = re.compile(
    r"(?:nộp đồ án|hạn nộp|nộp bài|deadline|hạn chót)\s*[:\-\—]?\s*([^\.\;\n]*?(?:ngày\s*)?\d+\s*(?:tháng|/)\s*\d+[^\.\;\n]*)",
    re.IGNORECASE,
)

ADMIN_GRADE_REGEX = re.compile(
    r"(?:công bố điểm|có điểm|chấm điểm|trả điểm)\s*[:\-\—]?\s*([^\.\;\n]*?(?:ngày\s*)?\d+\s*(?:tháng|/)\s*\d+[^\.\;\n]*)",
    re.IGNORECASE,
)

ADMIN_REMINDER_REGEX = re.compile(
    r"(?:lưu ý|nhắc nhở|chú ý|dặn dò|chuẩn đầu ra|bằng anh văn|chứng chỉ|bảo vệ tốt nghiệp)\s*[:\-\—]?\s*([^\.\;\n]+)",
    re.IGNORECASE,
)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def normalize_text(text: str) -> str:
    """Normalize unicode and standard spaces."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", normalized).strip()


def tokenize_words(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return [w.lower() for w in re.findall(r"[\wÀ-ỹ]+", text) if w.strip()]


def calculate_filler_density(line: str) -> float:
    """Calculate the ratio of filler words and phrases to total words in a sentence."""
    tokens = tokenize_words(line)
    if not tokens:
        return 1.0

    lower_line = line.lower()
    filler_word_hits = 0

    # Check multi-word fillers first
    for phrase in VIETNAMESE_FILLERS:
        if " " in phrase and phrase in lower_line:
            phrase_word_count = len(phrase.split())
            filler_word_hits += phrase_word_count

    # Check single-word fillers
    for token in tokens:
        if token in VIETNAMESE_FILLERS:
            filler_word_hits += 1

    return min(1.0, filler_word_hits / len(tokens))


def calculate_stutter_ratio(line: str) -> float:
    """Calculate the ratio of stuttered/repeated words to total words."""
    tokens = tokenize_words(line)
    if len(tokens) < 2:
        return 0.0
    stutter_matches = REPEATED_STUTTER_PATTERN.findall(line)
    # Each repetition match represents at least 2 tokens
    stuttered_tokens = len(stutter_matches) * 2
    return min(1.0, stuttered_tokens / len(tokens))


def is_low_quality_line(line: str) -> bool:
    """Determine if a sentence/line is conversational noise or ASR stutter artifact.

    Args:
        line: The text segment to evaluate.

    Returns:
        True if the line is low quality (should be omitted from topic summary),
        False if it represents clean, substantive content.
    """
    clean_line = normalize_text(line)
    if len(clean_line) < MIN_LINE_CHARS:
        return True

    tokens = tokenize_words(clean_line)
    if len(tokens) < MIN_TOKEN_COUNT:
        return True

    # Check letter count (exclude lines that are just numbers/symbols)
    letters = sum(ch.isalpha() for ch in clean_line)
    if letters < 8:
        return True

    # Check filler density
    filler_density = calculate_filler_density(clean_line)
    if filler_density >= MAX_FILLER_DENSITY:
        return True

    # Check stutter / ASR repetition ratio
    stutter_ratio = calculate_stutter_ratio(clean_line)
    if stutter_ratio >= MAX_STUTTER_RATIO:
        return True

    return False


# ==============================================================================
# TIER 1 SMART SUMMARY EXTRACTION
# ==============================================================================

def split_sentences(text: str) -> List[str]:
    """Split text into sentences based on punctuation and linebreaks."""
    raw_sentences = re.split(r"[\.\?\!\n]+", text)
    cleaned = []
    for s in raw_sentences:
        norm = normalize_text(s)
        if norm:
            cleaned.append(norm)
    return cleaned


def extract_smart_summary(text: str) -> Dict[str, Any]:
    """Extract Tier 1 provisional summary with independent channels for announcements & topics.

    Args:
        text: Raw or lightly processed transcript text.

    Returns:
        Dictionary containing:
            - announcements: List of administrative / logistical bullet points.
            - topic_summary: High-quality overview of technical/lecture topics.
            - topic_confidence: "LOW" or "MEDIUM" indicating confidence of provisional summary.
            - extracted_entities: Structured entity metadata.
    """
    if not text or not text.strip():
        return {
            "announcements": [],
            "topic_summary": "",
            "topic_confidence": "LOW",
            "extracted_entities": {
                "deadlines": [],
                "exam_dates": [],
                "presentations": [],
                "reminders": [],
                "grades": [],
            },
        }

    sentences = split_sentences(text)

    # --------------------------------------------------------------------------
    # Channel 1: Announcements & Administrative Milestones (Independent)
    # --------------------------------------------------------------------------
    announcements: List[str] = []
    entities: Dict[str, List[str]] = {
        "deadlines": [],
        "exam_dates": [],
        "presentations": [],
        "reminders": [],
        "grades": [],
    }

    # Extract Presentations
    pres_matches = ADMIN_PRESENTATION_REGEX.findall(text)
    if pres_matches:
        item = f"Thuyết trình: {pres_matches[0].strip()}"
        announcements.append(item)
        entities["presentations"].append(pres_matches[0].strip())

    # Extract Exam Dates
    exam_matches = ADMIN_EXAM_REGEX.findall(text)
    if exam_matches:
        item = f"Lịch thi lý thuyết: {exam_matches[0].strip()}"
        announcements.append(item)
        entities["exam_dates"].append(exam_matches[0].strip())

    # Extract Submission Deadlines
    subm_matches = ADMIN_SUBMISSION_REGEX.findall(text)
    if subm_matches:
        item = f"Hạn nộp đồ án: {subm_matches[0].strip()}"
        announcements.append(item)
        entities["deadlines"].append(subm_matches[0].strip())

    # Extract Grade Releases
    grade_matches = ADMIN_GRADE_REGEX.findall(text)
    if grade_matches:
        item = f"Công bố điểm: {grade_matches[0].strip()}"
        announcements.append(item)
        entities["grades"].append(grade_matches[0].strip())

    # Extract Key Reminders
    reminder_matches = ADMIN_REMINDER_REGEX.findall(text)
    if reminder_matches:
        clean_rem = reminder_matches[0].strip()[:90]
        item = f"Lưu ý: {clean_rem}"
        announcements.append(item)
        entities["reminders"].append(clean_rem)

    # --------------------------------------------------------------------------
    # Channel 2: Topic Summary (Independent - not excluded by announcements)
    # --------------------------------------------------------------------------
    quality_content_sentences: List[str] = []
    for s in sentences:
        if is_low_quality_line(s):
            continue
        # Avoid duplicating pure administrative announcement sentences in topic overview
        is_pure_admin = any(
            re.search(pat, s)
            for pat in [
                ADMIN_PRESENTATION_REGEX,
                ADMIN_EXAM_REGEX,
                ADMIN_SUBMISSION_REGEX,
                ADMIN_GRADE_REGEX,
            ]
        )
        if not is_pure_admin:
            quality_content_sentences.append(s)

    # Build topic summary string
    if quality_content_sentences:
        topic_summary = " · ".join(quality_content_sentences[:3])
        if len(topic_summary) > 220:
            topic_summary = topic_summary[:217] + "..."
    else:
        topic_summary = ""

    # --------------------------------------------------------------------------
    # Compute Topic Confidence (LOW vs MEDIUM for Tier 1 provisional)
    # --------------------------------------------------------------------------
    if len(quality_content_sentences) >= 2 and len(topic_summary) >= 40:
        topic_confidence = "MEDIUM"
    elif len(quality_content_sentences) == 1 and len(topic_summary) >= 25:
        topic_confidence = "MEDIUM"
    else:
        topic_confidence = "LOW"

    return {
        "announcements": announcements,
        "topic_summary": topic_summary,
        "topic_confidence": topic_confidence,
        "extracted_entities": entities,
    }


# ==============================================================================
# SUBJECT CLASSIFICATION WITH CONFIDENCE
# ==============================================================================

def classify_subject_with_confidence(
    scores: Dict[str, int],
    min_margin: float = 0.20,
    min_absolute_threshold: int = 12,
) -> Tuple[str, bool]:
    """Classify subject based on scored keywords, enforcing absolute threshold first then margin.

    Args:
        scores: Dictionary of candidate subjects to their integer match scores.
        min_margin: Minimum relative margin required over second-place score: (top - second) / top >= min_margin.
        min_absolute_threshold: Minimum absolute score required for top candidate before margin is considered.

    Returns:
        Tuple of (subject, is_confident):
            - subject: Name of top subject, or "none" if no candidates.
            - is_confident: True if top_score >= min_absolute_threshold AND margin criteria satisfied; False otherwise.
    """
    if not scores:
        return "none", False

    # Filter out candidates with zero or negative scores
    valid_scores = {k: int(v) for k, v in scores.items() if v > 0}
    if not valid_scores:
        return "none", False

    # Sort descending by score
    ranked = sorted(valid_scores.items(), key=lambda item: item[1], reverse=True)
    top_subject, top_score = ranked[0]

    # Rule 1: Enforce absolute threshold FIRST.
    # No branch can bypass min_absolute_threshold!
    if top_score < min_absolute_threshold:
        return top_subject, False

    # Rule 2: Single candidate (or second_score is 0) with top_score >= min_absolute_threshold
    if len(ranked) == 1:
        return top_subject, True

    second_subject, second_score = ranked[1]

    # If top and second are tied
    if top_score == second_score:
        return top_subject, False

    # Rule 3: Evaluate relative margin
    margin = (top_score - second_score) / float(top_score)
    if margin >= min_margin:
        return top_subject, True

    return top_subject, False
