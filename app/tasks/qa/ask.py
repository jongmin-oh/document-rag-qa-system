import re

from google import genai
from openai import OpenAI


from app.config import SEED, GeminiConfig
from app.index import body
from app.tasks.qa import Generated, GeneratedResponse, AskResponse, Citation, AskTrace
from app.tasks.qa.prompt import PERSONA
from app.tasks.qa.search import embed_query, rank, rewrite_with_version

TOP_K = 5
CITATION_GROUP = re.compile(r"\[((?:\d+\s*,\s*)*\d+)]")


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


def generation_client() -> genai.Client:
    if not GeminiConfig.API_KEY:
        raise ValueError(".env에 GEMINI_API_KEY를 설정하세요")
    # 429를 받으면 지수 백오프로 재시도한다.
    retry = {"attempts": 10, "initial_delay": 5, "max_delay": 60}
    return genai.Client(api_key=GeminiConfig.API_KEY, http_options={"retry_options": retry})


def answer(client: genai.Client, question: str, hits: list[tuple[float, dict]]) -> GeneratedResponse:
    context = "\n\n".join(f"[{i}] {c['title_prefix']} ({pages(c)}쪽)\n{body(c)}" for i, (_, c) in enumerate(hits, 1))
    response = client.models.generate_content(
        model=GeminiConfig.LLM_MODEL,
        contents=f"<documents>\n{context}\n</documents>\n\n<question>\n{question}\n</question>",
        config={
            "system_instruction": PERSONA,
            "temperature": 0,
            "seed": SEED,
            "thinking_config": {"thinking_level": "low"},
            "response_mime_type": "application/json",
            "response_schema": Generated,
        },
    )
    if response.parsed is None:
        raise ValueError("Gemini 답변 모델이 스키마에 맞는 응답을 반환하지 않았습니다")
    return GeneratedResponse(response.parsed, response.model_version)


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


def ask_with_trace(embedding_client: OpenAI, question: str, llm: genai.Client | None = None) -> AskTrace:
    """운영 ask와 같은 경로를 실행하고 평가에 필요한 중간 결과도 돌려준다."""
    llm = llm or generation_client()
    query, rewrite_model_version = rewrite_with_version(llm, question)
    hits = rank(embed_query(embedding_client, query), query, TOP_K)
    res = answer(llm, question, hits)
    return AskTrace(query, hits, build_response(res, hits), rewrite_model_version, res.parsed.answer)


def ask(embedding_client: OpenAI, question: str, llm: genai.Client | None = None) -> AskResponse:
    return ask_with_trace(embedding_client, question, llm).response
