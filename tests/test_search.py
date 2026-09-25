"""하이브리드 검색 구성요소 테스트. 실행: pytest tests"""

from app.tasks.qa.search import BM25, bigrams, rrf


def test_bigrams_ignore_whitespace():
    assert bigrams("실업 급여") == ["실업", "업급", "급여"]


def test_bm25_ranks_exact_term_first():
    bm25 = BM25(["조기재취업수당 지급 요건", "구직급여 지급 요건", "상병급여 청구"])
    scores = bm25.scores("조기재취업수당 받을 수 있나요")
    assert scores.index(max(scores)) == 0


def test_rrf_prefers_items_ranked_high_in_both():
    fused = [i for _, i in rrf([0, 1, 2], [1, 2, 0])]
    assert fused[0] == 1  # 두 순위에서 모두 상위(2위, 1위)
