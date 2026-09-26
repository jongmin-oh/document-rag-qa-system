"""하이브리드 검색 구성요소 테스트. 실행: pytest tests"""

from types import SimpleNamespace

from app.config import OPENROUTER_PROVIDER, SEED, OpenRouterConfig
from app.tasks.qa.search import BM25, bigrams, rewrite_with_version, rrf


def test_bigrams_ignore_whitespace():
    assert bigrams("실업 급여") == ["실업", "업급", "급여"]


def test_bm25_ranks_exact_term_first():
    bm25 = BM25(["조기재취업수당 지급 요건", "구직급여 지급 요건", "상병급여 청구"])
    scores = bm25.scores("조기재취업수당 받을 수 있나요")
    assert scores.index(max(scores)) == 0


def test_rrf_prefers_items_ranked_high_in_both():
    fused = [i for _, i in rrf([0, 1, 2], [1, 2, 0])]
    assert fused[0] == 1  # 두 순위에서 모두 상위(2위, 1위)


def test_rewrite_uses_openrouter_gemma_and_private_routing():
    class Completions:
        kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(
                model="google/gemma-4-31b-it",
                choices=[SimpleNamespace(message=SimpleNamespace(content="수급기간 연기"))],
            )

    completions = Completions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    text, version = rewrite_with_version(client, "군대 때문에 중지")

    assert text == "수급기간 연기"
    assert version == "google/gemma-4-31b-it"
    assert completions.kwargs["model"] == OpenRouterConfig.LLM_MODEL
    assert completions.kwargs["temperature"] == 0
    assert completions.kwargs["seed"] == SEED
    assert completions.kwargs["extra_body"]["provider"] == OPENROUTER_PROVIDER
