"""검색 지표 계산 테스트. 실행: pytest tests"""

from evaluation.retrieval import score


def span(doc, start, end, alt=()):
    return {"doc_id": doc, "char_start": start, "char_end": end, "alt": list(alt)}


def chunk(doc, start, end):
    return {"doc_id": doc, "char_start": start, "char_end": end}


def test_partial_coverage_below_threshold_is_not_recovered():
    evidence = [span("A", 0, 100), span("A", 200, 300)]
    chunks = [chunk("A", 0, 150), chunk("A", 200, 270), chunk("B", 0, 100)]
    s = score(evidence, chunks)
    assert s["recall"] == 0.5  # 첫 근거 100% 회수, 둘째는 70%만 덮여 미회수
    assert s["hit"] == 1.0
    assert s["coverage"] == (100 + 70) / 200
    assert s["precision"] == 2 / 3  # B 문서 청크는 근거와 겹치지 않음


def test_alt_counts_when_main_span_is_missed():
    evidence = [span("A", 0, 100, alt=[span("B", 50, 80)])]
    s = score(evidence, [chunk("B", 0, 100)])
    assert s["recall"] == 1.0 and s["coverage"] == 1.0 and s["precision"] == 1.0


def test_other_document_same_offsets_do_not_count():
    s = score([span("A", 0, 100)], [chunk("B", 0, 100)])
    assert s == {"hit": 0.0, "recall": 0.0, "coverage": 0.0, "precision": 0.0}
