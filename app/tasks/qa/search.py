"""검색: 조건별 인덱스에서 질문과 가까운 청크를 찾는다.

- dense: 질문 임베딩과 청크 임베딩의 코사인 유사도 (벡터를 정규화했으므로 내적)
- hybrid: dense 순위와 BM25 순위를 RRF로 합친다. BM25 토큰은 공백을 뺀 글자 2-gram이다.
  형태소 분석(kiwipiepy)과 비교했을 때 2-gram이 같거나 나았고 의존성도 없다 (decision/chunking_strategy.md 4절 H3).
  BM25·RRF 파라미터는 널리 쓰는 기본값으로 고정한다. Gold Set에 맞춰 조정하면 과적합이 된다.
"""

import math
import re
from collections import Counter
from functools import lru_cache

from google import genai

from app.tasks.index.build import body, embed, load_chunks, load_index

RETRIEVERS = {  # 검색 조건 → (인덱스 조건, BM25 결합 여부)
    "A": ("A", False),
    "B": ("B", False),
    "C": ("C", False),
    "C_hybrid": ("C", True),
}
SERVICE = "C"  # API·CLI가 쓰는 검색 조건
BM25_K1, BM25_B = 1.2, 0.75
RRF_K = 60


def bigrams(text: str) -> list[str]:
    t = re.sub(r"\s+", "", text)
    return [t[i : i + 2] for i in range(len(t) - 1)]


class BM25:
    def __init__(self, docs: list[str]):
        self.tf = [Counter(bigrams(d)) for d in docs]
        self.len = [sum(tf.values()) for tf in self.tf]
        self.avg = sum(self.len) / len(docs)
        df = Counter(t for tf in self.tf for t in tf)
        self.idf = {t: math.log(1 + (len(docs) - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def scores(self, query: str) -> list[float]:
        terms = set(bigrams(query)) & self.idf.keys()
        return [
            sum(
                self.idf[t] * tf[t] * (BM25_K1 + 1) / (tf[t] + BM25_K1 * (1 - BM25_B + BM25_B * n / self.avg))
                for t in terms
                if t in tf
            )
            for tf, n in zip(self.tf, self.len)
        ]


@lru_cache
def load(index: str):
    chunks = {c["chunk_id"]: c for c in load_chunks(index)}
    ids, vectors = load_index(index)
    ordered = [chunks[i] for i in ids]
    return ordered, vectors, BM25([c["title_prefix"] + "\n" + body(c) for c in ordered])


def embed_query(client: genai.Client, question: str) -> list[float]:
    # decision/models.md: 질의는 이 접두어로 문서와 구분한다.
    return embed(client, f"task: search result | query: {question}")


def rrf(*rankings: list[int]) -> list[tuple[float, int]]:
    score = Counter()
    for ranking in rankings:
        for rank, i in enumerate(ranking):
            score[i] += 1 / (RRF_K + rank + 1)
    return sorted(((s, i) for i, s in score.items()), reverse=True)


def rank(query_vec: list[float], question: str, retriever: str, k: int) -> list[tuple[float, dict]]:
    """(점수, 청크) top-k. 점수는 dense면 코사인 유사도, hybrid면 RRF 점수."""
    index, hybrid = RETRIEVERS[retriever]
    chunks, vectors, bm25 = load(index)
    # ponytail: 벡터 120개 전수 비교. 청크가 수만 개로 늘면 벡터 DB로 바꾼다.
    dense = sorted(((sum(a * b for a, b in zip(query_vec, v)), i) for i, v in enumerate(vectors)), reverse=True)
    if hybrid:
        keyword = sorted(((s, i) for i, s in enumerate(bm25.scores(question))), reverse=True)
        dense = rrf([i for _, i in dense], [i for _, i in keyword])
    return [(score, chunks[i]) for score, i in dense[:k]]
