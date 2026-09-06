"""Search agent coordinating query planning, two-phase hybrid search, and answer synthesis."""
from __future__ import annotations

from typing import List

from apps.aws.providers import get_runtime
from apps.domain import SearchHit, SearchPlan
from apps.search.vector_engine import hybrid_search


def execute_search(user_query: str) -> tuple[SearchPlan, List[SearchHit]]:
    """Execute a two-phase search for media records matching a natural language query.

    Phase 1 (Strict): Executes hybrid search applying all planner-extracted filters
    (media_type, category, subject) alongside keyword and vector similarity scoring.
    Phase 2 (Broadened): If strict filtering produces zero results, relaxes the
    metadata filters (media_type, category, subject) to search across the entire catalog
    with higher vector embedding weight.

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

    # Smart GSI Query: If planner identified a specific category, fetch records
    # via DynamoDB category-index GSI first to avoid full-table scans.
    candidate_records = None
    if plan.category and hasattr(runtime.catalog, "_query_by_category"):
        try:
            candidate_records = runtime.catalog._query_by_category(plan.category)
        except Exception:
            candidate_records = None

    if candidate_records is None:
        candidate_records = runtime.catalog.list_all()

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
    if not hits and (plan.media_type or plan.category or plan.subject):
        all_records = runtime.catalog.list_all()
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
