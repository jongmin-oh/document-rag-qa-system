"""질의 재작성 + 하이브리드 검색: LLM이 질문을 문서 용어로 바꾸고, 임베딩(dense) 순위와 BM25 순위를 RRF로 합친다.

- 재작성: 구어 질문("군입대로 중지")과 문서 용어("병역 복무로 인한 수급기간 연기")의 차이를 메운다.
- dense: 질문 임베딩과 청크 임베딩의 코사인 유사도 (벡터를 정규화했으므로 내적)
- BM25: 공백을 뺀 글자 2-gram. 형태소 분석(kiwipiepy)보다 같거나 나았고 의존성도 없다.
- BM25·RRF 파라미터는 널리 쓰는 기본값으로 고정한다. Gold Set에 맞춰 조정하면 과적합이 된다.
채택 근거(고정 길이·구조 기반·제목 접두어·하이브리드·질의 재작성 비교)는 decision/chunking_strategy.md 4절.
"""

import math
import re
from collections import Counter
from functools import lru_cache

from google import genai
from openai import OpenAI

from app.config import SEED, GeminiConfig
from app.tasks.index.build import body, embed, load_chunks, load_index

BM25_K1, BM25_B = 1.2, 0.75
RRF_K = 60
# 첫 버전 그대로 쓴다. 나빠진 문항을 보고 고치면 Gold Set에 과적합된다.
REWRITE = """아래 질문을 고용보험 실업급여 공식 안내 문서(법령 해설, 고용센터 안내 책자)에서 찾기 좋은 검색어 문장으로 바꿔 쓰세요.
- 구어·줄임말·상황 묘사를 문서에서 쓸 법한 공식 용어로 바꾸세요.
- 질문에 없는 사실이나 조건을 지어내지 마세요.
- 설명 없이 한두 문장만 출력하세요.

질문: {question}"""


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
def load():
    chunks = {c["chunk_id"]: c for c in load_chunks()}
    ids, vectors = load_index()
    ordered = [chunks[i] for i in ids]
    return ordered, vectors, BM25([c["title_prefix"] + "\n" + body(c) for c in ordered])


def rewrite_with_version(client: genai.Client, question: str) -> tuple[str, str]:
    res = client.models.generate_content(
        model=GeminiConfig.LLM_MODEL,
        contents=REWRITE.format(question=question),
        config={"temperature": 0, "seed": SEED, "thinking_config": {"thinking_level": "low"}},
    )
    if not res.text:
        raise ValueError("Gemini 질의 재작성 모델이 빈 응답을 반환했습니다")
    return res.text.strip(), res.model_version


def rewrite(client: genai.Client, question: str) -> str:
    return rewrite_with_version(client, question)[0]


def embed_query(client: OpenAI, question: str) -> list[float]:
    return embed(client, question)


def rrf(*rankings: list[int]) -> list[tuple[float, int]]:
    score = Counter()
    for ranking in rankings:
        for pos, i in enumerate(ranking):
            score[i] += 1 / (RRF_K + pos + 1)
    return sorted(((s, i) for i, s in score.items()), reverse=True)


def rank(query_vec: list[float], question: str, k: int) -> list[tuple[float, dict]]:
    """(RRF 점수, 청크) top-k."""
    chunks, vectors, bm25 = load()
    # ponytail: 벡터 120개 전수 비교. 청크가 수만 개로 늘면 벡터 DB로 바꾼다.
    dense = sorted(((sum(a * b for a, b in zip(query_vec, v)), i) for i, v in enumerate(vectors)), reverse=True)
    keyword = sorted(((s, i) for i, s in enumerate(bm25.scores(question))), reverse=True)
    return [(score, chunks[i]) for score, i in rrf([i for _, i in dense], [i for _, i in keyword])[:k]]
