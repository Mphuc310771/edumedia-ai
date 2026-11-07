from __future__ import annotations

from collections import defaultdict

from flashtext import KeywordProcessor

from apps.classify.text import fold_text


class WeightedKeywordIndex:
    """Aho-Corasick-style scan via FlashText: one pass over the text, O(N)."""

    def __init__(self, mapping: dict[str, tuple[tuple[str, int], ...]]):
        self.processor = KeywordProcessor(case_sensitive=False)
        self.payloads: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for key, keywords in mapping.items():
            for term, weight in keywords:
                folded = fold_text(term).strip()
                if not folded:
                    continue
                self.payloads[folded].append((key, int(weight)))
                self.processor.add_keyword(folded, folded)

    def matched_terms(self, text: str) -> set[str]:
        if not text:
            return set()
        return set(self.processor.extract_keywords(fold_text(text)))

    def score(self, labels_text: str, full_text: str) -> dict[str, int]:
        label_hits = self.matched_terms(labels_text)
        full_hits = self.matched_terms(full_text)
        scores: dict[str, int] = {}
        for folded in label_hits:
            for key, weight in self.payloads.get(folded, []):
                scores[key] = scores.get(key, 0) + int(weight * 1.5)
        for folded in full_hits - label_hits:
            for key, weight in self.payloads.get(folded, []):
                scores[key] = scores.get(key, 0) + weight
        return scores

    def best(self, labels_text: str, full_text: str) -> tuple[str | None, int]:
        scores = self.score(labels_text, full_text)
        if not scores:
            return None, 0
        key, value = max(scores.items(), key=lambda item: item[1])
        return key, value

    def contains_any(self, text: str) -> bool:
        return bool(self.matched_terms(text))
