from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List, Sequence

from apps.classify.flash_engine import WeightedKeywordIndex
from apps.classify.text import fold_text
from apps.classify.taxonomy import (
    CATEGORY_DESCRIPTIONS,
    CATEGORY_KEYWORDS,
    LECTURE_CONTEXT_HINTS,
    OCR_NOISE_BRANDS,
    SUBJECT_KEYWORDS,
    THRESHOLDS,
)
from apps.search.vector_engine import cosine_similarity, get_titan_embedding_with_source

CATEGORY_LOCK = int(THRESHOLDS.get("category_lock", 12))
CATEGORY_MIN = int(THRESHOLDS.get("category_min", 4))
SUBJECT_LOCK = int(THRESHOLDS.get("subject_lock", 12))
SUBJECT_MIN = int(THRESHOLDS.get("subject_min", 6))
VECTOR_MIN = float(THRESHOLDS.get("vector_min_cosine", 0.55))

DOCUMENT_LABEL_HINTS = (
    "whiteboard",
    "white board",
    "blackboard",
    "black board",
    "chalkboard",
    "mathematical equation",
    "bang viet",
    "bang den",
    "slide bai giang",
)

EXAM_HINTS = (
    "de thi",
    "bai tap",
    "bai giang",
    "hoc ky",
    "giao trinh",
    "dai hoc",
    "giang duong",
    "phuong trinh",
    "dao ham",
    "tich phan",
    "thuat toan",
    "qhtt",
)

RECEIPT_HINTS = (
    "hoa don",
    "tong tien",
    "thanh toan",
    "bien lai",
    "invoice",
    "receipt",
)

VISUAL_CATEGORIES = ("pets", "people", "food", "scenes")
TEXT_CATEGORIES = ("study", "receipts")

STREET_HINTS = (
    "street",
    "road",
    "tarmac",
    "car",
    "vehicle",
    "duong di",
    "duong pho",
    "nga tu",
    "o to",
    "xe co",
    "phuong tien",
)

PORTRAIT_HINTS = (
    "portrait",
    "selfie",
    "face",
    "khuon mat",
    "chan dung",
)


@lru_cache(maxsize=1)
def category_index() -> WeightedKeywordIndex:
    return WeightedKeywordIndex(CATEGORY_KEYWORDS)


@lru_cache(maxsize=1)
def subject_index() -> WeightedKeywordIndex:
    return WeightedKeywordIndex(SUBJECT_KEYWORDS)


@lru_cache(maxsize=1)
def lecture_index() -> WeightedKeywordIndex:
    mapping = {"lecture": tuple((hint, 1) for hint in LECTURE_CONTEXT_HINTS)}
    return WeightedKeywordIndex(mapping)


def _embed(text: str, bedrock_client=None) -> list[float]:
    vector, source = get_titan_embedding_with_source(text, bedrock_client=bedrock_client)
    if source == "titan" and vector:
        return vector
    return []


def _nearest(text: str | None, prototypes: dict[str, str], bedrock_client=None) -> tuple[str | None, float]:
    clean_text = (text or "").strip()
    if not clean_text or not prototypes:
        return None, 0.0
    query = _embed(clean_text, bedrock_client=bedrock_client)
    if not query:
        return None, 0.0
    ranked: list[tuple[str, float]] = []
    for key, description in prototypes.items():
        sim = cosine_similarity(query, _embed(description, bedrock_client=bedrock_client))
        ranked.append((key, sim))
    ranked.sort(key=lambda item: item[1], reverse=True)
    best_key, best_sim = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    if best_sim >= VECTOR_MIN and best_sim >= second + 0.08:
        return best_key, best_sim
    return None, best_sim


def _blob(*parts: str) -> str:
    return fold_text(" ".join(part for part in parts if part))


def _has_any(blob: str, phrases: Iterable[str]) -> bool:
    padded = f" {blob} "
    return any(f" {fold_text(phrase).strip()} " in padded for phrase in phrases if phrase)


def _clean_ocr_lines(text: str) -> list[str]:
    kept: list[str] = []
    for raw in (text or "").replace(",", "\n").splitlines():
        line = raw.strip()
        if len(line) < 4 or line.isdigit() or line.lower().startswith("http"):
            continue
        folded = fold_text(line)
        tokens = folded.split()
        if folded in OCR_NOISE_BRANDS or any(brand in tokens for brand in OCR_NOISE_BRANDS):
            continue
        if sum(ch.isalpha() for ch in line) < 3:
            continue
        kept.append(line)
    return kept


def _ocr_substantial(text: str) -> bool:
    lines = _clean_ocr_lines(text)
    alpha_chars = sum(sum(ch.isalpha() for ch in line) for line in lines)
    return len(lines) >= 3 and alpha_chars >= 60


def _is_document_like(labels: Sequence[str], text: str) -> bool:
    blob = _blob(*labels, text)
    return _has_any(blob, DOCUMENT_LABEL_HINTS) or _ocr_substantial(text)


def infer_category(media_type: str, labels: Sequence[str] | None, text: str | None, bedrock_client=None) -> str:
    if media_type == "video":
        return "videos"
    if media_type == "audio":
        return "study"

    safe_labels = list(labels or [])
    safe_text = text or ""
    labels_text = " ".join(safe_labels)
    full_text = f"{labels_text} {safe_text}"

    # 1. Multi-channel FlashText keyword scoring
    visual_scores = category_index().score(labels_text, labels_text)
    text_scores = category_index().score(labels_text, full_text)

    scores: dict[str, int] = {}
    for key in ("receipts", "scenes", "pets", "people", "food", "study"):
        vis = visual_scores.get(key, 0)
        txt = text_scores.get(key, 0)
        scores[key] = int(vis * 1.5 + txt)

    # 2. Context-aware category boosts + Computer Vision Layout Analysis
    if _has_any(_blob(safe_text), RECEIPT_HINTS):
        scores["receipts"] += 25

    from apps.classify.vision_layout import analyze_visual_layout
    layout = analyze_visual_layout(safe_labels, safe_text)
    if layout["is_scene_dominant"]:
        scores["scenes"] += 20
    if layout["is_living_dominant"]:
        for lk in ("pets", "people", "food"):
            if visual_scores.get(lk, 0) > 0:
                scores[lk] += 15

    subj = infer_subject(safe_labels, safe_text, "", "")
    if subj != "none":
        scores["study"] += 25  # Strong academic subject signal
    if _has_any(_blob(safe_text), EXAM_HINTS):
        scores["study"] += 20
    if _is_document_like(safe_labels, safe_text) and (subj != "none" or scores.get("study", 0) > 0):
        scores["study"] += 15

    # 3. Rank categories and evaluate confidence margin
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_cat, best_score = ranked[0]
    second_cat, second_score = ranked[1] if len(ranked) > 1 else ("other", 0)
    margin = best_score - second_score

    if best_score >= CATEGORY_MIN:
        if margin >= 2 or best_score >= CATEGORY_LOCK:
            return best_cat
        if subj == "none" and best_cat in VISUAL_CATEGORIES:
            return best_cat
        return best_cat

    # 4. Fallback to nearest prototype embedding
    prototypes = {key: value for key, value in CATEGORY_DESCRIPTIONS.items() if key not in {"videos"}}
    vector_key, _ = _nearest(full_text, prototypes, bedrock_client=bedrock_client)
    if vector_key:
        return vector_key
    return "other"


def infer_subject(
    labels: Sequence[str] | None,
    ocr_text: str | None = "",
    transcript: str | None = "",
    filename: str | None = "",
    bedrock_client=None,
) -> str:
    _ = bedrock_client
    full_text = " ".join([*(labels or []), ocr_text or "", transcript or "", filename or ""])
    if not fold_text(full_text).strip():
        return "none"
    best, score = subject_index().best("", full_text)
    if best and score >= SUBJECT_MIN:
        return best
    return "none"


def has_lecture_signal(parts: Iterable[str]) -> bool:
    blob = " ".join(part for part in parts if part)
    return lecture_index().contains_any(blob)
