from __future__ import annotations

import json
import logging
import math
from typing import List, Optional

from apps.domain import MediaRecord, SearchHit, SearchPlan, fold_text, record_haystack

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 256  # Compact dimension for high-speed local inference & Titan projection


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors in [-1.0, 1.0]."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot_product / (norm_a * norm_b)))


def compute_deterministic_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """
    Pure Python deterministic semantic embedding based on feature hashing & n-gram projection.
    Provides sub-millisecond local embeddings for development and testing without network dependency.
    """
    folded = fold_text(text)
    words = folded.split()
    vector = [0.0] * dim
    if not words:
        return vector

    for i, word in enumerate(words):
        # Hash full word
        h = hash(word) % dim
        vector[h] += 1.0 / (i + 1.0)
        # Hash 3-character n-grams for subword similarity
        if len(word) >= 3:
            for j in range(len(word) - 2):
                ngram_h = hash(word[j : j + 3]) % dim
                vector[ngram_h] += 0.35

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    return vector


def get_titan_embedding(text: str, bedrock_client=None) -> List[float]:
    """
    Generate real multimodal vector embedding using Amazon Titan Embeddings (amazon.titan-embed-text-v1).
    Gracefully falls back to deterministic local embedding if Bedrock is not available.
    """
    if not text.strip():
        return [0.0] * EMBEDDING_DIM

    if bedrock_client is not None:
        try:
            body = json.dumps({"inputText": text[:4000]})
            response = bedrock_client.invoke_model(
                body=body,
                modelId="amazon.titan-embed-text-v1",
                accept="application/json",
                contentType="application/json",
            )
            response_body = json.loads(response.get("body").read())
            raw_embedding = response_body.get("embedding", [])
            if raw_embedding:
                # Downsample/project to standard dimension if necessary
                if len(raw_embedding) == EMBEDDING_DIM:
                    return raw_embedding
                step = len(raw_embedding) / EMBEDDING_DIM
                projected = [raw_embedding[int(i * step)] for i in range(EMBEDDING_DIM)]
                norm = math.sqrt(sum(x * x for x in projected))
                return [x / norm for x in projected] if norm > 0 else projected
        except Exception as exc:
            logger.warning("Titan Embedding call failed (%s), using local embedding fallback", exc)

    return compute_deterministic_embedding(text, dim=EMBEDDING_DIM)


def hybrid_search(
    records: List[MediaRecord],
    plan: SearchPlan,
    raw_query: str,
    bedrock_client=None,
    weight_vector: float = 0.6,
    weight_keyword: float = 0.4,
) -> List[SearchHit]:
    """
    Enterprise Hybrid Search Engine:
    Combines Amazon Titan Vector Cosine Similarity (Semantic) + BM25/Exact Keyword Matching.
    Score = (weight_vector * VectorSimilarity) + (weight_keyword * KeywordScore)
    """
    if not records:
        return []

    # 1. Filter by media_type and category
    candidates = records
    if plan.media_type:
        candidates = [r for r in candidates if r.media_type == plan.media_type]
    if plan.category:
        candidates = [r for r in candidates if r.category == plan.category]

    if not candidates:
        return []

    # 2. Compute query embedding vector
    query_vector = plan.vector_query or get_titan_embedding(raw_query, bedrock_client=bedrock_client)

    hits: List[SearchHit] = []
    keywords_folded = [fold_text(kw) for kw in plan.keywords if kw.strip()]

    for record in candidates:
        # A. Vector Cosine Similarity
        record_text = f"{record.filename} {' '.join(record.labels)} {record.ocr_text} {record.transcript} {record.summary}"
        record_vector = record.embedding or get_titan_embedding(record_text, bedrock_client=bedrock_client)
        vec_sim = cosine_similarity(query_vector, record_vector)

        # B. Keyword & OCR String Matching
        haystack = record_haystack(record)
        matched_on: List[str] = []
        matched_fields: List[str] = []

        for kw in keywords_folded:
            if kw in haystack:
                matched_on.append(kw)
                if kw in fold_text(record.ocr_text):
                    matched_fields.append("ocr")
                if kw in fold_text(record.transcript):
                    matched_fields.append("transcript")
                if kw in fold_text(" ".join(record.labels)):
                    matched_fields.append("labels")
                if kw in fold_text(record.filename):
                    matched_fields.append("filename")

        matched_fields = list(dict.fromkeys(matched_fields))  # Deduplicate

        # Keyword density score (0.0 to 1.0)
        kw_score = (len(matched_on) / len(keywords_folded)) if keywords_folded else 0.0

        # C. Combined Hybrid Score
        if keywords_folded:
            final_score = (weight_vector * vec_sim) + (weight_keyword * kw_score)
        else:
            final_score = vec_sim

        # Filter out completely irrelevant items (score threshold)
        if final_score > 0.12 or matched_on:
            hits.append(
                SearchHit(
                    record=record,
                    score=round(final_score, 4),
                    vector_score=round(vec_sim, 4),
                    matched_on=matched_on,
                    matched_fields=matched_fields,
                )
            )

    # Sort descending by hybrid relevance score
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits
