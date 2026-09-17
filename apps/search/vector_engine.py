"""Vector similarity and hybrid search engine using Amazon Titan Embeddings."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from typing import List, Optional, Tuple

from apps.classify.text import fold_text
from apps.domain import MediaRecord, SearchHit, SearchPlan, matches_subject_filter, record_haystack

logger = logging.getLogger(__name__)

# Vector dimension: Subsampled from Titan's native 1536-d to 256-d to reduce
# DynamoDB storage costs and payload size while retaining directional similarity.
EMBEDDING_DIM = 256
_TITAN_SKIP_UNTIL = 0.0
_TITAN_RATE_COOLDOWN_SECONDS = 45


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculate the cosine similarity between two float vectors.

    Optimized with single-pass accumulation and unified norm calculation.

    Args:
        vec_a: First numeric vector.
        vec_b: Second numeric vector of the same dimension.

    Returns:
        Cosine similarity score bounded in the range [0.0, 1.0].
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot_product = 0.0
    norm_sq_a = 0.0
    norm_sq_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot_product += a * b
        norm_sq_a += a * a
        norm_sq_b += b * b
    if norm_sq_a <= 0.0 or norm_sq_b <= 0.0:
        return 0.0
    denom = math.sqrt(norm_sq_a * norm_sq_b)
    if denom <= 0.0:
        return 0.0
    return max(0.0, min(1.0, dot_product / denom))


def _stable_bucket(text: str, dim: int) -> int:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return int(digest, 16) % dim


def compute_deterministic_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Compute a stable hashed n-gram vector for unit tests.

    Not used as a Titan stand-in in production search; used to provide deterministic
    test vectors without requiring AWS credentials.

    Args:
        text: Input string to vectorize.
        dim: Target vector dimensionality (default: EMBEDDING_DIM=256).

    Returns:
        L2-normalized float vector of length `dim`.
    """
    folded = fold_text(text)
    words = folded.split()
    vector = [0.0] * dim
    if not words:
        return vector

    for i, word in enumerate(words):
        vector[_stable_bucket(word, dim)] += 1.0 / (i + 1.0)
        if len(word) >= 3:
            for j in range(len(word) - 2):
                vector[_stable_bucket(word[j : j + 3], dim)] += 0.35

    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    return vector


def get_titan_embedding_with_source(text: str, bedrock_client=None) -> Tuple[List[float], str]:
    """Generate a vector embedding for text using Amazon Titan Text Embeddings on Bedrock.

    Downsamples raw Titan embeddings (1536 dimensions) to 256 dimensions to minimize
    DynamoDB storage costs and payload size while retaining directional semantic similarity.

    Args:
        text: Input text string to embed (truncated to first 4000 characters).
        bedrock_client: Optional boto3 Bedrock Runtime client.

    Returns:
        Tuple of (embedding vector as list of floats, source identifier 'titan' or 'off').
    """
    global _TITAN_SKIP_UNTIL
    if not text.strip():
        return [0.0] * EMBEDDING_DIM, "off"
    if bedrock_client is None:
        return [], "off"
    if time.time() < _TITAN_SKIP_UNTIL:
        return [], "off"
    try:
        raw_embedding = []
        # Ưu tiên dùng Amazon Titan Embeddings v2 với native 256 dimensions và L2 normalization
        try:
            body_v2 = json.dumps({"inputText": text[:4000], "dimensions": EMBEDDING_DIM, "normalize": True})
            response = bedrock_client.invoke_model(
                body=body_v2,
                modelId="amazon.titan-embed-text-v2:0",
                accept="application/json",
                contentType="application/json",
            )
            response_body = json.loads(response.get("body").read())
            raw_embedding = response_body.get("embedding", [])
        except Exception as v2_err:
            # Fallback về Titan v1 nếu tài khoản chưa bật v2
            logger.debug("Titan v2 unavailable (%s), falling back to Titan v1", v2_err)
            body_v1 = json.dumps({"inputText": text[:4000]})
            response = bedrock_client.invoke_model(
                body=body_v1,
                modelId="amazon.titan-embed-text-v1",
                accept="application/json",
                contentType="application/json",
            )
            response_body = json.loads(response.get("body").read())
            raw_embedding = response_body.get("embedding", [])

        if not raw_embedding:
            return [], "off"
        if len(raw_embedding) == EMBEDDING_DIM:
            return raw_embedding, "titan"
        # Subsample vector từ 1536 xuống 256 chiều nếu rơi vào fallback Titan v1
        step = len(raw_embedding) / EMBEDDING_DIM
        projected = [raw_embedding[int(i * step)] for i in range(EMBEDDING_DIM)]
        norm = math.sqrt(sum(x * x for x in projected))
        return ([x / norm for x in projected] if norm > 0 else projected), "titan"
    except Exception as exc:
        message = str(exc).lower()
        if "throttling" in message or "too many requests" in message:
            _TITAN_SKIP_UNTIL = time.time() + _TITAN_RATE_COOLDOWN_SECONDS
            logger.warning("Titan rate-limited. Skip embeddings for %ss.", _TITAN_RATE_COOLDOWN_SECONDS)
        else:
            logger.warning("Titan Embedding call failed (%s)", exc)
        return [], "off"


def get_titan_embedding(text: str, bedrock_client=None) -> List[float]:
    vector, source = get_titan_embedding_with_source(text, bedrock_client=bedrock_client)
    return vector if source == "titan" else []


def maybe_store_embedding(text: str, bedrock_client=None) -> Optional[List[float]]:
    vector, source = get_titan_embedding_with_source(text, bedrock_client=bedrock_client)
    return vector if source == "titan" else None


def hybrid_search(
    records: List[MediaRecord],
    plan: SearchPlan,
    raw_query: str,
    bedrock_client=None,
    weight_vector: float = 0.6,
    weight_keyword: float = 0.4,
) -> Tuple[List[SearchHit], str]:
    """Perform hybrid search combining vector cosine similarity and keyword matching.

    Filters candidate records by search plan criteria, calculates weighted hybrid
    relevance scores, and returns sorted results.

    Args:
        records: List of MediaRecord items to search.
        plan: SearchPlan containing metadata filters and keywords.
        raw_query: Raw natural language query for vector embedding generation.
        bedrock_client: Optional boto3 Bedrock Runtime client.
        weight_vector: Relative weight for vector similarity score (default: 0.6).
        weight_keyword: Relative weight for keyword match score (default: 0.4).

    Returns:
        Tuple of (sorted list of SearchHit objects, embedding source indicator).
    """
    if not records:
        return [], "off"

    candidates = records
    if plan.media_type:
        candidates = [r for r in candidates if r.media_type == plan.media_type]
    if plan.category:
        candidates = [r for r in candidates if r.category == plan.category]
    if plan.subject:
        candidates = [r for r in candidates if matches_subject_filter(r, plan.subject)]
    if not candidates:
        return [], "off"

    query_vector, embedding_source = get_titan_embedding_with_source(
        raw_query, bedrock_client=bedrock_client
    )
    use_vector = embedding_source == "titan" and bool(query_vector)

    hits: List[SearchHit] = []
    keywords_folded = [fold_text(kw) for kw in plan.keywords if kw.strip()]

    for record in candidates:
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
                if kw in fold_text(record.summary):
                    matched_fields.append("summary")

        matched_fields = list(dict.fromkeys(matched_fields))
        kw_score = (len(matched_on) / len(keywords_folded)) if keywords_folded else 0.0

        vec_sim = 0.0
        if use_vector and record.embedding:
            vec_sim = cosine_similarity(query_vector, record.embedding)

        if use_vector and keywords_folded:
            final_score = (weight_vector * vec_sim) + (weight_keyword * kw_score)
        elif use_vector:
            final_score = vec_sim
        else:
            final_score = kw_score

        if use_vector:
            keep = final_score > 0.12 or bool(matched_on)
        else:
            keep = bool(matched_on) or not keywords_folded

        if keep:
            hits.append(
                SearchHit(
                    record=record,
                    score=round(final_score, 4),
                    vector_score=round(vec_sim, 4),
                    matched_on=matched_on,
                    matched_fields=matched_fields,
                )
            )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits, ("titan" if use_vector else "off")
