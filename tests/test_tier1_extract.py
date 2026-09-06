import pytest

from pipeline.tier1_extract import (
    classify_subject_with_confidence,
    extract_smart_summary,
    is_low_quality_line,
)


# ==============================================================================
# TESTS: is_low_quality_line
# ==============================================================================

def test_low_quality_line_short_or_empty():
    assert is_low_quality_line("") is True
    assert is_low_quality_line("   ") is True
    assert is_low_quality_line("ừ đúng rồi") is True
    assert is_low_quality_line("ok nhé") is True


def test_low_quality_line_high_filler_density():
    # Dense filler lines from spoken conversational speech
    filler_line = "ờ thì là mà nói chung là kiểu như vậy đó thành ra là"
    assert is_low_quality_line(filler_line) is True

    mixed_filler_line = "thì là ờ các em hình dung không kiểu như là vậy đó"
    assert is_low_quality_line(mixed_filler_line) is True


def test_low_quality_line_stutter_repetition():
    stutter_line = "cứ cứ làm làm chạy chạy với với một số cái nào đó"
    assert is_low_quality_line(stutter_line) is True


def test_high_quality_substantive_line():
    good_line_1 = "Hôm nay chúng ta sẽ tìm hiểu về kiến trúc Serverless và Amazon DynamoDB"
    assert is_low_quality_line(good_line_1) is False

    good_line_2 = "Mô hình quan hệ thực thể ERD bao gồm các thực thể thuộc tính và khóa chính"
    assert is_low_quality_line(good_line_2) is False


# ==============================================================================
# TESTS: extract_smart_summary
# ==============================================================================

def test_extract_smart_summary_independent_channels():
    text = (
        "Các nhóm chuẩn bị phần trình bày 10 phút mỗi nhóm. "
        "Lịch thi lý thuyết vào ngày 17 tháng 7 và hạn nộp đồ án ngày 24 tháng 7. "
        "Hôm nay chúng ta học về thuật toán Round Robin và Virtual Memory trong hệ điều hành. "
        "Kỹ thuật phân trang Paging giúp giảm thiểu phân mảnh bộ nhớ ngoài."
    )
    result = extract_smart_summary(text)

    # 1. Announcements must be extracted
    assert len(result["announcements"]) >= 3
    assert any("Thuyết trình" in a for a in result["announcements"])
    assert any("17 tháng 7" in a for a in result["announcements"])
    assert any("24 tháng 7" in a for a in result["announcements"])

    # 2. Topic summary must NOT be skipped (independent extraction channel)
    assert result["topic_summary"] != ""
    assert "Round Robin" in result["topic_summary"]
    assert "Paging" in result["topic_summary"]

    # 3. Topic confidence should be MEDIUM for high-quality substantive content
    assert result["topic_confidence"] == "MEDIUM"
    assert result["extracted_entities"]["deadlines"]
    assert result["extracted_entities"]["exam_dates"]


def test_extract_smart_summary_pure_announcements():
    text = (
        "Lịch thi lý thuyết ngày 17 tháng 7. "
        "Hạn nộp đồ án ngày 24 tháng 7. "
        "Công bố điểm ngày 31 tháng 7."
    )
    result = extract_smart_summary(text)
    assert len(result["announcements"]) == 3
    # When there are only admin dates, topic summary should be empty/low confidence
    assert result["topic_confidence"] == "LOW"


def test_extract_smart_summary_empty_text():
    result = extract_smart_summary("")
    assert result["announcements"] == []
    assert result["topic_summary"] == ""
    assert result["topic_confidence"] == "LOW"
    assert isinstance(result["extracted_entities"], dict)


# ==============================================================================
# TESTS: classify_subject_with_confidence
# ==============================================================================

def test_classify_empty_scores():
    subject, is_confident = classify_subject_with_confidence({})
    assert subject == "none"
    assert is_confident is False


def test_classify_single_score_below_absolute_threshold():
    # Absolute threshold = 12. Score = 8 -> NOT confident even though only 1 candidate
    subject, is_confident = classify_subject_with_confidence({"math": 8}, min_margin=0.20, min_absolute_threshold=12)
    assert subject == "math"
    assert is_confident is False


def test_classify_single_score_above_absolute_threshold():
    # Absolute threshold = 12. Score = 15 -> Confident
    subject, is_confident = classify_subject_with_confidence({"math": 15}, min_margin=0.20, min_absolute_threshold=12)
    assert subject == "math"
    assert is_confident is True


def test_classify_tied_top_scores():
    # Both os and cloud have 16 points -> Tied -> NOT confident
    subject, is_confident = classify_subject_with_confidence({"os": 16, "cloud": 16}, min_margin=0.20, min_absolute_threshold=12)
    assert subject in {"os", "cloud"}
    assert is_confident is False


def test_classify_top_below_threshold_ahead_of_second():
    # Top score 10 < threshold 12, second score 2 -> Must be False because absolute threshold is enforced first!
    subject, is_confident = classify_subject_with_confidence({"os": 10, "cloud": 2}, min_margin=0.20, min_absolute_threshold=12)
    assert subject == "os"
    assert is_confident is False


def test_classify_top_above_threshold_with_sufficient_margin():
    # Top 20 >= 12, second 12. Margin = (20 - 12) / 20 = 0.40 >= 0.20 -> True
    subject, is_confident = classify_subject_with_confidence({"cloud": 20, "os": 12}, min_margin=0.20, min_absolute_threshold=12)
    assert subject == "cloud"
    assert is_confident is True


def test_classify_top_above_threshold_with_insufficient_margin():
    # Top 20 >= 12, second 18. Margin = (20 - 18) / 20 = 0.10 < 0.20 -> False
    subject, is_confident = classify_subject_with_confidence({"cloud": 20, "os": 18}, min_margin=0.20, min_absolute_threshold=12)
    assert subject == "cloud"
    assert is_confident is False
