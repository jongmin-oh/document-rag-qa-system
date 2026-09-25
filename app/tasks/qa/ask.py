"""질문 → 청크 검색 → 근거를 인용한 답변 생성.

사용법: python -m app.tasks.qa.ask "질문"
먼저 python -m app.tasks.index.build 로 인덱스를 만들어야 한다.
"""

import sys

from google import genai

from app.config import GeminiConfig
from app.tasks.index.build import body, client, embed, load_chunks, load_index

TOP_K = 5
SYSTEM = """당신은 고용보험 실업급여 안내 도우미입니다. 아래 [자료]만 근거로, 법령을 모르는 사람도 이해할 수 있게 쉬운 한국어로 답하세요.
- 자료에 없는 내용은 추측하지 말고 "제공된 자료에서 찾을 수 없습니다. 고용노동부 고객상담센터(국번 없이 1350)에 문의하세요."라고만 답하세요.
- 근거로 쓴 문장 끝에 자료 번호를 [1]처럼 표시하세요.
- 자료마다 기준일이 다릅니다. 내용이 서로 다르면 두 내용을 기준일과 함께 모두 알려 주세요."""


def pages(c: dict) -> str:
    return f"{c['page_start']}" + (f"–{c['page_end']}" if c["page_end"] != c["page_start"] else "")


def search(client: genai.Client, question: str) -> list[tuple[float, dict]]:
    chunks = {c["chunk_id"]: c for c in load_chunks()}
    ids, vectors = load_index()
    # decision/models.md: 질의는 이 접두어로 문서와 구분한다.
    q = embed(client, f"task: search result | query: {question}")
    # ponytail: 벡터 120개 전수 비교(정규화했으므로 내적 = 코사인). 청크가 수만 개로 늘면 벡터 DB로 바꾼다.
    scored = sorted(((sum(a * b for a, b in zip(q, v)), ids[i]) for i, v in enumerate(vectors)), reverse=True)
    return [(score, chunks[cid]) for score, cid in scored[:TOP_K]]


def answer(client: genai.Client, question: str, hits: list[tuple[float, dict]]):
    context = "\n\n".join(f"[{i}] {c['title_prefix']} ({pages(c)}쪽)\n{body(c)}" for i, (_, c) in enumerate(hits, 1))
    return client.models.generate_content(
        model=GeminiConfig.LLM_MODEL,
        contents=f"[자료]\n{context}\n\n[질문]\n{question}",
        config={"system_instruction": SYSTEM, "temperature": 0, "thinking_config": {"thinking_level": "low"}},
    )


def main():
    question = " ".join(sys.argv[1:])
    if not question:
        sys.exit('사용법: python -m app.tasks.qa.ask "질문"')
    gemini = client()
    hits = search(gemini, question)
    res = answer(gemini, question, hits)
    print(res.text, "\n\n[자료]")
    for i, (score, c) in enumerate(hits, 1):
        print(f"[{i}] {score:.3f} {c['chunk_id']} {c['title_prefix']} ({pages(c)}쪽)")
    print(f"\nmodel_version: {res.model_version}")


if __name__ == "__main__":
    main()
