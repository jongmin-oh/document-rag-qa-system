"""End-to-end 답변 평가의 결정론적 지표 테스트."""

from types import SimpleNamespace

from app.tasks.eval.answer import deterministic, summarize
from app.tasks.qa.ask import AskResponse, AskTrace, Citation, Generated, build_response, citation_numbers, clean_answer


def item(answerability="full", evidence=True):
    return {
        "answerability": answerability,
        "evidence": (
            [{"doc_id": "A", "char_start": 0, "char_end": 100, "alt": []}] if evidence else []
        ),
    }


def trace(answer="근거 있는 답 [1]", answerable=True, citations=(1,)):
    hits = [
        (
            0.03,
            {
                "chunk_id": "A-0001",
                "doc_id": "A",
                "char_start": 0,
                "char_end": 100,
                "title_prefix": "문서 A",
                "page_start": 1,
                "page_end": 1,
                "question_prefix": "",
                "text": "근거",
            },
        ),
        (
            0.02,
            {
                "chunk_id": "B-0001",
                "doc_id": "B",
                "char_start": 0,
                "char_end": 100,
                "title_prefix": "문서 B",
                "page_start": 1,
                "page_end": 1,
                "question_prefix": "",
                "text": "다른 내용",
            },
        ),
    ]
    response = AskResponse(
        answerable=answerable,
        answer=answer,
        citations=[
            Citation(
                n=n,
                chunk_id=hits[n - 1][1]["chunk_id"],
                source=hits[n - 1][1]["title_prefix"],
                page_start=1,
                page_end=1,
                score=hits[n - 1][0],
            )
            for n in citations
        ],
        model_version="test-model",
    )
    return AskTrace("검색 질의", hits, response, "test-model", answer)


def test_answer_and_citation_match_gold_evidence():
    result = deterministic(item(), trace())
    assert result["answerability_correct"]
    assert result["citation_integrity"]
    assert result["citation_presence_correct"]
    assert result["evidence"] == {"hit": 1.0, "recall": 1.0, "coverage": 1.0, "precision": 1.0}


def test_inline_and_response_citations_must_match():
    result = deterministic(item(), trace(answer="잘못된 번호 [2]", citations=(1,)))
    assert not result["citation_integrity"]


def test_citation_numbers_supports_single_and_grouped_notation():
    assert citation_numbers("첫 주장 [1], 다음 주장 [2, 4], 다시 [1]") == [1, 2, 4]


def test_clean_answer_removes_internal_citations_and_extra_spaces():
    assert clean_answer("첫 주장 [1]. 다음 주장 [2, 4]!") == "첫 주장. 다음 주장!"
    assert clean_answer("앞 [1] 뒤") == "앞 뒤"


def test_api_citations_are_derived_from_answer_text():
    generated = SimpleNamespace(
        parsed=Generated(answerable=True, answer="근거 [2, 1]"),
        model_version="test-model",
    )
    response = build_response(generated, trace().hits)
    assert [c.n for c in response.citations] == [2, 1]
    assert response.answer == "근거"


def test_answer_needs_inline_citation_even_if_response_lists_one():
    result = deterministic(item(), trace(answer="본문에는 인용 표시가 없음", citations=(1,)))
    assert not result["citation_integrity"]
    assert not result["citation_presence_correct"]


def test_unanswerable_refusal_has_no_citation():
    result = deterministic(
        item(answerability="none", evidence=False),
        trace(answer="제공된 자료에서 찾을 수 없습니다.", answerable=False, citations=()),
    )
    assert result["answerability_correct"]
    assert result["citation_integrity"]
    assert result["citation_presence_correct"]
    assert result["evidence"] is None


def test_summary_reports_false_answers_and_raw_refusal_count():
    base_judge = {"correctness": 4, "completeness": 4, "faithfulness": 4, "partial_handling": -1}
    rows = [
        {
            "answerability": "none",
            "response": {"answerable": False},
            "deterministic": deterministic(
                item(answerability="none", evidence=False),
                trace(answer="거부", answerable=False, citations=()),
            ),
            "judge": base_judge,
        },
        {
            "answerability": "none",
            "response": {"answerable": True},
            "deterministic": deterministic(item(answerability="none", evidence=False), trace()),
            "judge": base_judge,
        },
    ]
    result = summarize(rows)
    assert result["refusal_recall"] == 0.5
    assert result["false_answer_rate"] == 0.5
    assert result["refused"] == 1 and result["n_none"] == 2
