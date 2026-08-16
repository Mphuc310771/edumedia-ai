from __future__ import annotations

from typing import List

from apps.aws.providers import get_runtime
from apps.domain import SearchHit, SearchPlan
from apps.search.vector_engine import hybrid_search


def execute_search(user_query: str) -> tuple[SearchPlan, List[SearchHit]]:
    runtime = get_runtime()
    plan = runtime.planner.plan(user_query)
    all_records = runtime.catalog.list_all()
    bedrock_client = getattr(runtime.planner, "client", None)

    # Execute Hybrid Semantic Vector + Keyword Search
    hits = hybrid_search(
        records=all_records,
        plan=plan,
        raw_query=user_query,
        bedrock_client=bedrock_client,
        weight_vector=0.6,
        weight_keyword=0.4,
    )

    # Broaden query if strict filters returned 0 results
    if not hits and (plan.media_type or plan.category):
        broadened_plan = SearchPlan(
            keywords=plan.keywords,
            media_type=None,
            category=None,
            rationale=f"{plan.rationale} | broadened after strict filter",
        )
        hits = hybrid_search(
            records=all_records,
            plan=broadened_plan,
            raw_query=user_query,
            bedrock_client=bedrock_client,
            weight_vector=0.7,
            weight_keyword=0.3,
        )
        plan = broadened_plan

    runtime.metrics.emit("MediaQueries", 1)
    return plan, hits[:12]
