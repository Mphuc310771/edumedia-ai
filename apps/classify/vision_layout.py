"""Computer Vision Spatial Layout & Geometry Analysis Engine."""

from __future__ import annotations

from typing import Sequence
from apps.classify.text import fold_text


# High-confidence visual landscape / architecture / living scene markers
SCENERY_VISUAL_MARKERS = {
    "mountain", "landscape", "beach", "sunset", "sunrise", "ocean", "nature",
    "scenery", "altar", "temple", "pagoda", "church", "prayer", "worship",
    "resort", "garden", "urban", "forest", "tree", "plant", "water", "sea",
    "thien nhien", "ngoai troi", "bien ca", "mat nuoc", "phong canh", "canh vat",
    "nui non", "nui ba den", "chua", "chua chien", "ban tho", "den tho", "nha tho",
    "hoa tuoi", "binh hoa", "cay coi", "tham thuc vat", "cay xanh"
}

# High-confidence living entity markers
LIVING_ENTITY_MARKERS = {
    "dog", "cat", "tiger", "mammal", "pet", "animal", "bird",
    "cho", "meo", "thu cung", "dong vat",
    "person", "human", "man", "woman", "boy", "girl", "face", "portrait",
    "con nguoi", "chan dung", "khuon mat", "cau thu",
    "food", "dish", "meal", "seafood", "plate", "drink", "coffee",
    "mon an", "hai san", "dia an", "bua an", "do uong"
}

# Strict academic classroom / document layout markers
ACADEMIC_LAYOUT_MARKERS = {
    "whiteboard", "white board", "blackboard", "black board", "chalkboard",
    "mathematical equation", "bang viet", "bang den", "slide bai giang",
    "giao trinh", "de thi", "bai tap lon"
}


def analyze_visual_layout(labels: Sequence[str], ocr_text: str) -> dict:
    """Perform Computer Vision layout & visual dominance analysis on Rekognition output."""
    folded_labels = [fold_text(label).strip() for label in labels if label]
    label_blob = " ".join(folded_labels)

    # 1. Count scene & living entity visual hits
    scene_hits = sum(1 for m in SCENERY_VISUAL_MARKERS if m in label_blob)
    living_hits = sum(1 for m in LIVING_ENTITY_MARKERS if m in label_blob)
    academic_hits = sum(1 for m in ACADEMIC_LAYOUT_MARKERS if m in label_blob)

    # 2. Text layout density
    clean_lines = [l.strip() for l in ocr_text.splitlines() if len(l.strip()) >= 4]
    line_count = len(clean_lines)
    total_alpha = sum(sum(ch.isalpha() for ch in l) for l in clean_lines)
    is_dense_document = line_count >= 4 and total_alpha >= 80

    # 3. Dominance decision
    is_scene_dominant = scene_hits >= 2 and not is_dense_document and academic_hits == 0
    is_living_dominant = living_hits >= 2 and not is_dense_document and academic_hits == 0

    return {
        "scene_hits": scene_hits,
        "living_hits": living_hits,
        "academic_hits": academic_hits,
        "is_dense_document": is_dense_document,
        "is_scene_dominant": is_scene_dominant,
        "is_living_dominant": is_living_dominant,
        "line_count": line_count,
        "total_alpha": total_alpha,
    }
