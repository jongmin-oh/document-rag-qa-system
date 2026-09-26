from dataclasses import dataclass
from pydantic import BaseModel, Field


class Generated(BaseModel):
    """LLM 구조화 출력."""

    answerable: bool = Field(description="자료로 질문에 답할 수 있으면 true, 자료에 답이 전혀 없으면 false")
    answer: str


@dataclass
class GeneratedResponse:
    parsed: Generated
    model_version: str


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
