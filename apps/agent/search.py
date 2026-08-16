from __future__ import annotations

from typing import List

from apps.aws.providers import get_runtime
from apps.domain import SearchHit, SearchPlan, fold_text, record_haystack


def execute_search(user_query: str) -> tuple[SearchPlan, List[SearchHit]]:
    runtime = get_runtime()
    plan = runtime.planner.plan(user_query)
    records = runtime.catalog.search(plan)
    if not records and (plan.media_type or plan.category):
        broadened = SearchPlan(keywords=plan.keywords, rationale="broadened after empty filter")
        records = runtime.catalog.search(broadened)
        plan = SearchPlan(
            keywords=plan.keywords,
            media_type=None,
            category=None,
            rationale=f"{plan.rationale} | broadened",
        )

    hits: List[SearchHit] = []
    for index, record in enumerate(records):
        haystack = record_haystack(record)
        matched = [kw for kw in plan.keywords if fold_text(kw) in haystack]
        fields = []
        if any(fold_text(kw) in fold_text(record.ocr_text) for kw in plan.keywords):
            fields.append("ocr")
        if any(fold_text(kw) in fold_text(record.transcript) for kw in plan.keywords):
            fields.append("transcript")
        if any(fold_text(kw) in fold_text(" ".join(record.labels)) for kw in plan.keywords):
            fields.append("labels")
        if any(fold_text(kw) in fold_text(record.summary) for kw in plan.keywords):
            fields.append("summary")
        score = 1.0 - (index * 0.08)
        if matched:
            score = min(1.0, 0.55 + 0.15 * len(matched))
        hits.append(
            SearchHit(
                record=record,
                score=round(score, 3),
                matched_on=matched,
                matched_fields=fields,
            )
        )
    hits.sort(key=lambda hit: hit.score, reverse=True)
    runtime.metrics.emit("MediaQueries", 1)
    return plan, hits[:12]
