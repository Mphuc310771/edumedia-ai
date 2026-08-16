from apps.aws.memory import MemoryPlanner
from apps.agent.search import execute_search
from apps.domain import SearchPlan


def test_planner_extracts_exam_intent():
    plan = MemoryPlanner().plan("Tìm đoạn thầy dặn thi cuối kỳ trong file ghi âm")
    assert plan.media_type == "audio"
    assert plan.category == "study"
    assert any("thi" in kw.lower() for kw in plan.keywords)


def test_search_exam_hit_cites_transcript():
    _, hits = execute_search("Tìm đoạn thầy dặn thi cuối kỳ")
    assert hits
    assert "transcript" in hits[0].matched_fields
    assert hits[0].matched_on



def test_search_can_filter_pets():
    _, hits = execute_search("Tìm ảnh chú chó lông vàng")
    assert hits
    assert hits[0].record.category == "pets"


def test_search_unaccented_vietnamese():
    _, hits = execute_search("Tim anh cho long vang")
    assert hits
    assert any(hit.record.category == "pets" for hit in hits)




def test_search_plan_blank_media_type():
    plan = SearchPlan.model_validate({"keywords": ["aws"], "media_type": "", "category": "study"})
    assert plan.media_type is None
    assert plan.category == "study"


def test_category_inference_photo_label_not_receipt():
    from apps.domain import infer_category

    # Rekognition often tags general photos with "Photo" / "Photography"
    category = infer_category("image", ["Photo", "Dog", "Mammal"], "Golden retriever dog")
    assert category == "pets"

    # Actual receipts
    receipt_cat = infer_category("image", ["Document", "Paper"], "Hóa đơn tiền điện VAT: 100000 VND")
    assert receipt_cat == "receipts"


def test_bedrock_plan_json_resilience():
    from apps.aws.aws_services import _parse_bedrock_plan_json

    # Test markdown fenced json
    fenced = '```json\n{"keywords": ["dog", "cat"], "media_type": "image", "category": "pets", "rationale": "ok"}\n```'
    plan = _parse_bedrock_plan_json(fenced, "tim cho meo")
    assert plan.category == "pets"
    assert "dog" in plan.keywords

    # Test invalid json fallback
    invalid = 'Sorry, I cannot format this as json directly.'
    fallback_plan = _parse_bedrock_plan_json(invalid, "tim chu cho vang")
    assert fallback_plan.rationale == "Fallback keyword extraction from query"
    assert "cho" in fallback_plan.keywords or "chu" in fallback_plan.keywords


def test_vector_cosine_similarity():
    from apps.search.vector_engine import cosine_similarity, compute_deterministic_embedding

    v1 = compute_deterministic_embedding("toán cao cấp tích phân")
    v2 = compute_deterministic_embedding("toán tích phân giải tích")
    v3 = compute_deterministic_embedding("chú chó lông vàng ngoài sân")

    sim_related = cosine_similarity(v1, v2)
    sim_unrelated = cosine_similarity(v1, v3)

    assert sim_related > 0.4
    assert sim_related > sim_unrelated


def test_hybrid_vector_semantic_search():
    from apps.agent.search import execute_search

    # Test abstract semantic query
    _, hits = execute_search("tài liệu học tập giảng đường")
    assert hits
    assert any(h.record.category == "study" for h in hits)
    assert hits[0].score > 0.0

