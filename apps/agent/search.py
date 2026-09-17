"""Search agent coordinating query planning, two-phase hybrid search, and answer synthesis."""
from __future__ import annotations

from typing import List

from apps.aws.providers import get_runtime
from apps.domain import SearchHit, SearchPlan
from apps.search.vector_engine import hybrid_search


CANDIDATE_POOL_LIMIT: int = 100


def _fetch_candidate_pool(catalog, category: str | None = None, limit: int = CANDIDATE_POOL_LIMIT) -> List:
    """Fetch candidate records respecting the hard limit and avoiding unbounded scans."""
    records = None
    if category and hasattr(catalog, "_query_by_category"):
        try:
            records = catalog._query_by_category(category, limit=limit)
        except TypeError:
            records = catalog._query_by_category(category)
        except Exception:
            records = None

    if records is None:
        try:
            records = catalog.list_all(limit=limit)
        except TypeError:
            records = catalog.list_all()

    if records and len(records) > limit:
        records = records[:limit]
    return records or []


def execute_search(user_query: str) -> tuple[SearchPlan, List[SearchHit]]:
    """Execute a two-phase search for media records matching a natural language query.

    Phase 1 (Strict): Executes hybrid search applying all planner-extracted filters
    (media_type, category, subject) alongside keyword and vector similarity scoring.
    Phase 2 (Broadened): If strict filtering produces zero results, relaxes the
    metadata filters (media_type, category, subject) to search across the entire catalog
    with higher vector embedding weight.

    Candidate Pool: Limited to a hard cap of 100 newest items to prevent unbounded
    DynamoDB Full Table Scans and control Lambda RAM consumption.

    Args:
        user_query: Natural language query string from the user.

    Returns:
        A tuple of (SearchPlan, list of top SearchHit items up to 12).
    """
    runtime = get_runtime()
    plan = runtime.planner.plan(user_query)
    if not user_query.strip():
        plan.embedding_source = "off"
        runtime.metrics.emit("MediaQueries", 1)
        return plan, []

    bedrock_client = getattr(runtime.planner, "client", None)

    # Smart GSI Query / Capped Candidate Pool:
    # Query via DynamoDB category-index GSI first if available, otherwise fetch
    # up to CANDIDATE_POOL_LIMIT (100) newest items to calculate Cosine Similarity.
    candidate_records = _fetch_candidate_pool(runtime.catalog, plan.category, limit=CANDIDATE_POOL_LIMIT)

    hits, embedding_source = hybrid_search(
        records=candidate_records,
        plan=plan,
        raw_query=user_query,
        bedrock_client=bedrock_client,
        weight_vector=0.6,
        weight_keyword=0.4,
    )

    # Phase 2 Broadening: When strict metadata constraints (media_type, category, subject)
    # yield zero hits, broaden the search scope by removing these filters while keeping
    # keywords, and increase vector similarity weight (0.6 -> 0.7) to maximize semantic recall.
    # The broadened candidate pool is also capped at CANDIDATE_POOL_LIMIT (100).
    if not hits and (plan.media_type or plan.category or plan.subject):
        all_records = _fetch_candidate_pool(runtime.catalog, category=None, limit=CANDIDATE_POOL_LIMIT)
        broadened_plan = SearchPlan(
            keywords=plan.keywords,
            media_type=None,
            category=None,
            subject=None,
            rationale=f"{plan.rationale} | broadened after strict filter",
            planner_source=plan.planner_source,
        )
        hits, embedding_source = hybrid_search(
            records=all_records,
            plan=broadened_plan,
            raw_query=user_query,
            bedrock_client=bedrock_client,
            weight_vector=0.7,
            weight_keyword=0.3,
        )
        plan = broadened_plan

    plan.embedding_source = embedding_source

    if hasattr(runtime.planner, "synthesize_answer") and hits and not plan.direct_answer:
        direct_ans, snippet, src = runtime.planner.synthesize_answer(user_query, hits)
        if direct_ans:
            plan.direct_answer = direct_ans
            plan.evidence_snippet = snippet
            plan.source_file = src

    runtime.metrics.emit("MediaQueries", 1)
    return plan, hits[:12]
