from apps.agent.search import execute_search
from apps.domain import SearchPlan, infer_subject


def test_query_infers_exam_and_subject():
    assert infer_subject([], "Tìm slide IELTS tiếng Anh", "", "") == "english"
    assert infer_subject([], "Tài liệu môn tự chọn ngoài ngành", "", "") == "off_major"


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


def test_search_empty_query_returns_no_hits():
    _, hits = execute_search("")
    assert hits == []


def test_category_inference_photo_label_not_receipt():
    from apps.domain import infer_category

    category = infer_category("image", ["Photo", "Dog", "Mammal"], "Golden retriever dog")
    assert category == "pets"

    receipt_cat = infer_category("image", ["Document", "Paper"], "Hóa đơn tiền điện VAT: 100000 VND")
    assert receipt_cat == "receipts"


def test_infer_subject_from_ocr_and_transcript():
    from apps.domain import infer_subject, resolve_subject
    from apps.domain import MediaRecord

    assert infer_subject([], "Toán Cao Cấp - Tích Phân", "", "board.jpg") == "math"
    assert infer_subject([], "", "Round Robin và Virtual Memory, Page Fault", "aud.mp3") == "os"
    assert infer_subject([], "AWS Lambda DynamoDB Serverless", "", "slide.jpg") == "cloud"
    assert infer_subject([], "Tiếng Anh chuyên ngành - IELTS Reading", "", "eng.jpg") == "english"
    assert infer_subject([], "Vật lý đại cương - Quang học", "", "phy.jpg") == "physics"
    assert infer_subject([], "Môn tự chọn ngoài ngành: kỹ năng mềm", "", "soft.jpg") == "off_major"
    assert infer_subject(["Dog", "Mammal", "Hổ"], "CHEEWID", "", "tiger.jpg") == "none"
    assert infer_subject(["Hoa tươi", "Nam giới"], "", "", "hoa.jpg") == "none"

    board = MediaRecord(
        file_id="board",
        filename="lecture.jpg",
        s3_key="uploads/board.jpg",
        media_type="image",
        content_type="image/jpeg",
        category="study",
        labels=["Whiteboard", "Classroom"],
    )
    assert resolve_subject(board) == "lecture"

    people = MediaRecord(
        file_id="x",
        filename="ronaldo.jpg",
        s3_key="uploads/x.jpg",
        media_type="image",
        content_type="image/jpeg",
        category="people",
        labels=["Person", "Face"],
    )
    assert resolve_subject(people) == "none"


def test_workspace_photo_is_not_a_lecture():
    from apps.domain import MediaRecord, infer_category, resolve_subject, usable_ocr_text

    ocr = "700AH\nWHIS\nRedmi K40\nSHAVER ***\nKho, Ant, No, Co, BÔ"
    assert usable_ocr_text(ocr) == ""

    category = infer_category(
        "image",
        ["Computer", "Electronics", "Laptop", "PC", "Hardware"],
        ocr,
    )
    assert category == "other"

    desk = MediaRecord(
        file_id="desk",
        filename="20260731_205742_lmc_8.4.jpg",
        s3_key="uploads/desk.jpg",
        media_type="image",
        content_type="image/jpeg",
        category="study",
        subject="lecture",
        labels=["Computer", "Electronics", "Laptop"],
        ocr_text=ocr,
    )
    assert resolve_subject(desk) == "none"


def test_search_by_subject_keywords():
    _, math_hits = execute_search("tích phân")
    assert math_hits
    assert any(hit.record.subject == "math" for hit in math_hits)

    _, os_hits = execute_search("Round Robin")
    assert os_hits
    assert any(hit.record.subject == "os" for hit in os_hits)

    _, en_hits = execute_search("IELTS")
    assert en_hits
    assert any(hit.record.subject == "english" for hit in en_hits)


def test_bedrock_plan_json_resilience():
    from apps.aws.aws_services import _parse_bedrock_plan_json

    fenced = '```json\n{"keywords": ["dog", "cat"], "media_type": "image", "category": "pets", "rationale": "ok"}\n```'
    plan = _parse_bedrock_plan_json(fenced, "tim cho meo")
    assert plan.category == "pets"
    assert "dog" in plan.keywords

    invalid = "Sorry, I cannot format this as json directly."
    fallback_plan = _parse_bedrock_plan_json(invalid, "tim chu cho vang")
    assert fallback_plan.rationale == "Bedrock unavailable — keyword fallback"
    assert "cho" in fallback_plan.keywords or "chu" in fallback_plan.keywords


def test_bedrock_daily_quota_uses_keyword_fallback():
    from apps.aws import aws_services

    aws_services._BEDROCK_SKIP_UNTIL = 0
    assert aws_services._is_daily_token_throttle(
        RuntimeError("ThrottlingException: Too many tokens per day, please wait before trying again.")
    )
    assert not aws_services._is_daily_token_throttle(
        RuntimeError("ThrottlingException: Too many requests, please wait before trying again.")
    )
    assert aws_services._is_rate_throttle(
        RuntimeError("ThrottlingException: Too many requests, please wait before trying again.")
    )
    aws_services._mark_bedrock_daily_quota()
    assert aws_services._bedrock_quota_blocked()
    plan = aws_services._heuristic_search_plan("tìm IELTS tiếng Anh", "quota")
    assert plan.planner_source == "heuristic"
    assert plan.subject == "english"
    aws_services._BEDROCK_SKIP_UNTIL = 0


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
    _, hits = execute_search("tài liệu học tập giảng đường")
    assert hits
    assert any(h.record.category == "study" for h in hits)
    assert hits[0].score > 0.0


def test_taxonomy_lives_outside_python():
    from pathlib import Path
    from apps.classify.taxonomy import CATEGORY_KEYWORDS, SUBJECT_KEYWORDS, load_taxonomy

    yaml_path = Path(__file__).resolve().parents[1] / "apps" / "taxonomy.yaml"
    assert yaml_path.exists()
    data = load_taxonomy()
    assert "pets" in data["categories"]
    assert "math" in data["subjects"]
    assert CATEGORY_KEYWORDS["pets"]
    assert SUBJECT_KEYWORDS["os"]


def test_flashtext_one_pass_category_score():
    from apps.classify.engine import category_index

    scores = category_index().score("Dog Pet Mammal", "Golden retriever dog")
    assert scores["pets"] >= 12


def test_infer_media_type_uses_mime_registry():
    from apps.domain import infer_media_type

    assert infer_media_type("lecture.webp", "") == "image"
    assert infer_media_type("talk.m4a", "audio/mp4") == "audio"
    assert infer_media_type("clip.mkv", "") == "video"
    assert infer_media_type("notes.bin", "application/octet-stream") == "other"


def test_webp_converts_to_jpeg_for_rekognition():
    from io import BytesIO
    from PIL import Image
    from apps.aws.image_convert import image_bytes_to_jpeg, needs_rekognition_convert

    assert needs_rekognition_convert("1.webp")
    assert not needs_rekognition_convert("board.jpg")

    buf = BytesIO()
    Image.new("RGB", (80, 80), color=(12, 80, 160)).save(buf, format="WEBP")
    jpeg = image_bytes_to_jpeg(buf.getvalue())
    assert jpeg[:2] == b"\xff\xd8"
    opened = Image.open(BytesIO(jpeg))
    assert opened.format == "JPEG"
    assert opened.size == (80, 80)


def test_whiteboard_with_person_is_study_not_people():
    from apps.domain import infer_category, infer_subject

    category = infer_category(
        "image",
        ["White board", "Boy", "Person", "Human", "Text"],
        "Vd1 max 2x+y\nThuat toan\nS.C. x+y <= 1",
    )
    assert category == "study"
    assert infer_subject(["White board", "Person"], "Cau 4. Ky vong so. Thuat toan", "", "board.jpg") == "programming"


def test_exam_paper_is_study_not_receipt():
    from apps.domain import infer_category, infer_subject

    ocr = "TRUONG DAI HOC KHOA HOC TU NHIEN\nDE THI GIUA KY\nHoc ky 2 - Nam hoc 2026"
    category = infer_category("image", ["Document", "Paper", "Receipt", "Text"], ocr)
    assert category == "study"
    assert infer_subject(["Receipt"], ocr, "", "exam.jpg") != "programming"


def test_macroeconomics_slide_is_study_economics():
    from apps.domain import infer_category, infer_subject

    ocr = "CAP NHAT KINH TE VI MO VIET NAM\nNhung dien bien kinh te gan day"
    assert infer_category("image", ["Page", "Text", "Advertisement", "Poster"], ocr) == "study"
    assert infer_subject(["Page", "Text"], ocr, "", "bao-cao-kinh-te.png") == "economics"


def test_formula_sheet_is_study_math():
    from apps.domain import infer_category, infer_subject

    ocr = "(sin x)' = cos x\n(tan x)' = 1 + tan2 x\nDao ham"
    assert infer_category("image", ["Text", "Document", "Mathematical equation"], ocr) == "study"
    assert infer_subject(["Mathematical equation"], ocr, "", "dao-ham-2026.jpg") == "math"


def test_whiteboard_ocr_cho_is_not_a_dog():
    from apps.domain import infer_category

    category = infer_category(
        "image",
        ["White board", "Person", "Text"],
        "cho min (a)xx\nlat cat s tnho\nQhtt linear programming",
    )
    assert category == "study"


def test_landscape_vat_collision_is_not_receipt():
    from apps.domain import infer_category

    category = infer_category(
        "image",
        ["Cây cối", "Cảnh vật", "Thiên nhiên", "Ngoài trời"],
        "",
    )
    assert category != "receipts"

    from apps.classify.engine import infer_category

    category = infer_category("image", ["Outdoor"], "cún vàng chạy trên thảm cỏ")
    assert category in {"pets", "scenes", "other"}


def test_parse_bedrock_plan_with_rag_answer():
    from apps.aws.aws_services import _parse_bedrock_plan_json

    json_text = """
    {
      "search_plan": {
        "keywords": ["mạng máy tính", "định tuyến", "chương 3", "router"],
        "media_type": "audio",
        "category": "study",
        "subject": "networks",
        "rationale": "Tìm ghi âm dặn thi môn mạng"
      },
      "rag_answer": {
        "has_answer": true,
        "direct_answer": "Thầy dặn ôn tập trọng tâm Chương 3 định tuyến IP.",
        "evidence_snippet": "Các em ôn kỹ chương 3 định tuyến nhé.",
        "source_file": "bai_giang_tuan_10.mp3",
        "confidence": "high"
      }
    }
    """
    plan = _parse_bedrock_plan_json(json_text, "Thầy dặn thi môn mạng chương mấy")
    assert plan.planner_source == "bedrock"
    assert "mạng máy tính" in plan.keywords
    assert plan.media_type == "audio"
    assert plan.subject == "networks"
    assert plan.direct_answer == "Thầy dặn ôn tập trọng tâm Chương 3 định tuyến IP."
    assert plan.evidence_snippet == "Các em ôn kỹ chương 3 định tuyến nhé."
    assert plan.source_file == "bai_giang_tuan_10.mp3"


def test_bedrock_planner_cache_hit():
    from apps.aws.aws_services import BedrockPlanner, _PLAN_CACHE
    from apps.domain import SearchPlan

    planner = BedrockPlanner()
    query = "Toán Giải Tích 12"
    cache_key = query.strip().lower()

    # Pre-populate cache
    cached_plan = SearchPlan(
        keywords=["toán", "giải tích"],
        category="study",
        subject="math",
        rationale="Cached test plan",
        planner_source="bedrock",
    )
    import time
    _PLAN_CACHE[cache_key] = (time.time(), cached_plan)

    # Call plan() on cached query -> returns cached plan instantly without calling Bedrock
    plan = planner.plan(query)
    assert plan.keywords == ["toán", "giải tích"]
    assert plan.rationale == "Cached test plan"
    assert plan.subject == "math"


def test_search_candidate_pool_limit_and_chunk_exclusion(monkeypatch):
    from apps.agent.search import CANDIDATE_POOL_LIMIT, _fetch_candidate_pool
    from apps.aws.providers import get_runtime
    from apps.domain import MediaRecord

    assert CANDIDATE_POOL_LIMIT == 100

    # Test candidate pool capping
    runtime = get_runtime()
    # Insert a chunk item directly into runtime table
    runtime.catalog.table.put_item(
        Item={"file_id": "seed-aws-slide#CHUNK#0001", "parent_file_id": "seed-aws-slide", "text": "chunk"}
    )

    # Test _fetch_candidate_pool excludes chunks and caps at limit
    pool = _fetch_candidate_pool(runtime.catalog, category="study", limit=2)
    assert len(pool) <= 2
    assert not any("#CHUNK#" in r.file_id for r in pool)

    # Test search execution never returns chunks
    _, hits = execute_search("Serverless S3 DynamoDB")
    assert hits
    assert not any("#CHUNK#" in hit.record.file_id for hit in hits)




