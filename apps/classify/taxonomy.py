from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "taxonomy.yaml"


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    with TAXONOMY_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def _keyword_map(section: dict[str, Any]) -> dict[str, tuple[tuple[str, int], ...]]:
    mapping: dict[str, tuple[tuple[str, int], ...]] = {}
    for key, spec in (section or {}).items():
        pairs = tuple(
            (str(item["term"]), int(item["weight"]))
            for item in spec.get("keywords") or []
            if item.get("term")
        )
        mapping[key] = pairs
    return mapping


def _labels(section: dict[str, Any], extra: dict[str, str] | None = None) -> dict[str, str]:
    labels = {key: str(spec.get("label") or key) for key, spec in (section or {}).items()}
    if extra:
        labels.update(extra)
    return labels


def _descriptions(section: dict[str, Any]) -> dict[str, str]:
    return {key: str(spec.get("description") or spec.get("label") or key) for key, spec in (section or {}).items()}


taxonomy = load_taxonomy()
CATEGORY_KEYWORDS = _keyword_map(taxonomy.get("categories") or {})
SUBJECT_KEYWORDS = _keyword_map(taxonomy.get("subjects") or {})
CATEGORY_LABELS = _labels(taxonomy.get("categories") or {})
SUBJECT_LABELS = _labels(taxonomy.get("subjects") or {}, extra={"none": ""})
CATEGORY_DESCRIPTIONS = _descriptions(taxonomy.get("categories") or {})
SUBJECT_DESCRIPTIONS = _descriptions(taxonomy.get("subjects") or {})
LECTURE_CONTEXT_HINTS = tuple(str(item) for item in taxonomy.get("lecture_hints") or [])
OCR_NOISE_BRANDS = {str(item).lower() for item in taxonomy.get("ocr_noise_brands") or []}
THRESHOLDS = taxonomy.get("thresholds") or {}

OFF_MAJOR_SUBJECTS = {
    key
    for key, spec in (taxonomy.get("subjects") or {}).items()
    if spec.get("off_major")
}
MAJOR_SUBJECTS = {
    key
    for key, spec in (taxonomy.get("subjects") or {}).items()
    if spec.get("major")
} | {"lecture"}
