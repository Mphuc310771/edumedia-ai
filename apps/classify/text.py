from __future__ import annotations

import unicodedata


def fold_text(value: str) -> str:
    """Lowercase and strip Vietnamese diacritics so 'cho' matches 'chó' and 'de' matches 'đề'."""
    normalized = unicodedata.normalize("NFD", value or "")
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    stripped = stripped.replace("đ", "d").replace("Đ", "d")
    return stripped.lower().replace("-", " ").replace("_", " ")
