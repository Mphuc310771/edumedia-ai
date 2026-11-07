from apps.agent.search import execute_search
from apps.aws.providers import get_runtime


def test_end_to_end_query_after_seed():
    catalog = get_runtime().catalog.list_all()
    assert catalog
    plan, hits = execute_search("Tìm slide bài giảng AWS")
    assert hits
    assert any("AWS" in (hit.record.ocr_text + hit.record.summary) for hit in hits)
    assert plan.category in {"study", None}
