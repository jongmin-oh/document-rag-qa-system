"""질문 → 청크 검색 → 근거를 인용한 답변 생성.

사용법: python -m app.tasks.qa.ask "질문"  (API는 main.py)
먼저 python -m app.tasks.index.build 로 인덱스를 만들어야 한다.
"""

import re
import sys
from dataclasses import dataclass

from google import genai
from pydantic import BaseModel, Field

from app.config import GeminiConfig
from app.tasks.index.build import body, client
from app.tasks.qa.search import embed_query, rank, rewrite_with_version

TOP_K = 5
CITATION_GROUP = re.compile(r"\[((?:\d+\s*,\s*)*\d+)]")
SYSTEM = """당신은 고용보험 실업급여 안내 도우미입니다. 아래 [자료]만 근거로, 법령을 모르는 사람도 이해할 수 있게 쉬운 한국어로 답하세요.
- 자료에 답이 전혀 없으면 추측하지 말고 answerable을 false로 하고, answer에는 "제공된 자료에서 찾을 수 없습니다. 고용노동부 고객상담센터(국번 없이 1350)에 문의하세요."라고만 쓰세요.
- 일부만 답할 수 있으면 answerable을 true로 하고, 답할 수 없는 부분은 자료에 없다고 밝히세요.
- 근거로 쓴 문장 끝에 자료 번호를 [1]처럼 표시하고, 표시한 번호를 모두 citations에 넣으세요.
- 자료마다 기준일이 다릅니다. 내용이 서로 다르면 두 내용을 기준일과 함께 모두 알려 주세요."""


class Generated(BaseModel):
    """LLM 구조화 출력."""

    answerable: bool = Field(description="자료로 질문에 답할 수 있으면 true, 자료에 답이 전혀 없으면 false")
    answer: str


class Citation(BaseModel):
    n: int  # answer 안의 [n]
    chunk_id: str
    source: str  # "[문서 | 기준일] 제목 > 경로"
    page_start: int  # 인쇄 쪽
    page_end: int
    score: float  # 하이브리드 검색의 RRF 점수


class AskResponse(BaseModel):
    answerable: bool  # false면 응답 불가(자료에 답이 없음)
    answer: str
    citations: list[Citation]
    model_version: str


@dataclass
class AskTrace:
    """평가기에서 쓰는 검색·생성 전체 실행 기록. API 응답에는 노출하지 않는다."""

    rewritten_query: str
    hits: list[tuple[float, dict]]
    response: AskResponse
    rewrite_model_version: str
    annotated_answer: str


def pages(c: dict) -> str:
    return f"{c['page_start']}" + (f"–{c['page_end']}" if c["page_end"] != c["page_start"] else "")


def citation_numbers(answer: str) -> list[int]:
    """본문의 [1]과 [1, 3] 형식에서 번호를 등장 순서대로 중복 없이 뽑는다."""
    numbers = (int(n.strip()) for group in CITATION_GROUP.findall(answer) for n in group.split(","))
    return list(dict.fromkeys(numbers))


def clean_answer(answer: str) -> str:
    """내부 인용 번호를 사용자에게 보여 줄 답변에서 제거한다."""
    cleaned = CITATION_GROUP.sub("", answer)
    cleaned = re.sub(r"[ \t]+([.,!?])", r"\1", cleaned)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def answer(client: genai.Client, question: str, hits: list[tuple[float, dict]]):
    context = "\n\n".join(f"[{i}] {c['title_prefix']} ({pages(c)}쪽)\n{body(c)}" for i, (_, c) in enumerate(hits, 1))
    return client.models.generate_content(
        model=GeminiConfig.LLM_MODEL,
        contents=f"[자료]\n{context}\n\n[질문]\n{question}",
        config={
            "system_instruction": SYSTEM,
            "temperature": 0,
            "thinking_config": {"thinking_level": "low"},
            "response_mime_type": "application/json",
            "response_schema": Generated,
        },
    )


def build_response(res, hits: list[tuple[float, dict]]) -> AskResponse:
    out: Generated = res.parsed
    # 본문을 인용 번호의 단일 기준으로 삼고, 검색된 자료에 없는 번호는 버린다.
    cited = [n for n in citation_numbers(out.answer) if 1 <= n <= len(hits)] if out.answerable else []
    return AskResponse(
        answerable=out.answerable,
        answer=clean_answer(out.answer),
        citations=[
            Citation(
                n=n,
                chunk_id=c["chunk_id"],
                source=c["title_prefix"],
                page_start=c["page_start"],
                page_end=c["page_end"],
                score=round(score, 4),
            )
            for n in cited
            for score, c in [hits[n - 1]]
        ],
        model_version=res.model_version,
    )


def ask_with_trace(client: genai.Client, question: str) -> AskTrace:
    """운영 ask와 같은 경로를 실행하고 평가에 필요한 중간 결과도 돌려준다."""
    query, rewrite_model_version = rewrite_with_version(client, question)
    hits = rank(embed_query(client, query), query, TOP_K)
    res = answer(client, question, hits)
    return AskTrace(query, hits, build_response(res, hits), rewrite_model_version, res.parsed.answer)


def ask(client: genai.Client, question: str) -> AskResponse:
    return ask_with_trace(client, question).response


def main():
    question = " ".join(sys.argv[1:])
    if not question:
        sys.exit('사용법: python -m app.tasks.qa.ask "질문"')
    res = ask(client(), question)
    print(res.answer, "\n")
    for c in res.citations:
        print(f"[{c.n}] {c.score:.3f} {c.chunk_id} {c.source} ({pages(c.model_dump())}쪽)")
    print(f"\nanswerable: {res.answerable} / model_version: {res.model_version}")


if __name__ == "__main__":
    main()
