"""Gold Set 빌드 테스트. 실행: pytest tests"""

import pytest

from evaluation.gold.build import build, fold, locate


def test_gold_set_builds():
    """모든 인용문이 canonical text에서 한 번씩 찾아지고, 답할 수 없는 문항만 근거가 비어 있다."""
    items = build()
    assert all(bool(i["evidence"]) == (i["answerability"] != "none") for i in items)


def test_locate_ignores_whitespace_and_compat_hanja():
    text = fold("가 나\n다(離職) 라 마")  # 원문의 離는 호환 문자 U+F9EA
    assert locate(text, "나 다(離職) ... 마") == (2, 13)


def test_locate_rejects_ambiguous_quote():
    with pytest.raises(ValueError):
        locate("가나 가나", "가나")
