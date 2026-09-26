"""Markdown 원문과 청커 회귀 테스트. 실행: pytest tests"""

import re

import pytest

from preprocessing.ingest.build import build
from preprocessing.ingest.chunker import HEADING, SOFT_LIMIT
from preprocessing.ingest.laws import cited_laws

EL = "easylaw_unemployment_benefit"
BK = "work24_employment_dream_booklet"


@pytest.fixture(scope="module")
def built():
    return build()


def chunks(built, doc_id=None):
    return [c for d, (_, cs) in built.items() if doc_id in (None, d) for c in cs]


def find(built, doc_id, needle):
    return next(c for c in chunks(built, doc_id) if needle in c.text)


# --- 청킹 규칙
def test_q10_split_with_question_prefix(built):
    q10 = [c for c in chunks(built, BK) if c.section_path[-1].startswith("Q10.")]
    assert len(q10) == 2
    assert not q10[0].question_prefix
    assert q10[1].question_prefix.startswith("Q. Q10.")


def test_qa_never_merged(built):
    for c in chunks(built, BK):
        assert len(re.findall(r"^## Q\d", c.text, re.M)) <= 1


def test_size_limit_except_single_block(built):
    for c in chunks(built):
        assert c.n_chars <= SOFT_LIMIT or "\n\n" not in c.text.strip()


def test_no_heading_only_chunks(built):
    for c in chunks(built):
        assert any(l.strip() and not HEADING.match(l) for l in c.text.split("\n")), c.chunk_id


def test_canonical_offsets(built):
    for canonical, cs in built.values():
        for c in cs:
            assert canonical[c.char_start : c.char_end] == c.text
        assert "<!--" not in canonical


def test_group_heading_in_path(built):
    card = find(built, BK, "### 1. 국민내일배움카드")
    assert card.section_path[:2] == ["취업지원 프로그램", "직업능력개발 지원"]


def test_page_ranges(built):
    for c in chunks(built, EL):
        assert 4 <= c.page_start <= c.page_end <= 59
    for c in chunks(built, BK):
        assert 3 <= c.page_start <= c.page_end <= 68
    assert find(built, EL, "소정급여일수의 산정").page_start in (24, 25)


# --- 표
def test_benefit_days_table(built):
    c = find(built, EL, "표: 소정급여일수의 산정")
    row = "| 이직일 현재 연령 50세 이상 및 장애인 | 120일 | 180일 | 210일 | 240일 | 270일 |"
    assert row in c.text and "피보험기간 1년 이상 3년 미만" in c.text
    assert "고용보험법 제50조제1항" in c.cited_laws


def test_benefit_types_tree(built):
    assert "- 구직급여 > 연장급여 > 개별연장급여" in find(built, EL, "표: 실업급여의 종류").text


def test_reemployment_activity_table(built):
    c = find(built, BK, "| 수급자 유형 | 실업인정 차수 |")
    for kind in ("① 일반수급자", "② 반복수급자", "③ 만 60세 이상"):
        assert kind in c.text
    assert "| ① 일반수급자 | 4차~7차 실업인정일 | 4주 2회 | 구직활동 1회 이상 반드시 포함 |" in c.text


def test_single_contact_chunk(built):
    contact = [c for c in chunks(built, BK) if "실업급여에 대해 궁금한 점이 있다면?" in c.text]
    assert len(contact) == 1 and contact[0].page_start == 68


# --- 법령 추출
@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "(「고용보험법」 제45조제5항, 제46조제1항제1호 및 「고용보험법 시행령」 제\n68조제1항)",
            ["고용보험법 제45조제5항", "고용보험법 제46조제1항제1호", "고용보험법 시행령 제68조제1항"],
        ),
        ("(「근로기준법」 제2조제1항제5호·제6호)", ["근로기준법 제2조제1항제5호", "근로기준법 제2조제1항제6호"]),
        ("「고용보험법」 제43조제1항·제2항·제4항 참조", ["고용보험법 제43조제1항", "고용보험법 제43조제2항", "고용보험법 제43조제4항"]),
        ("「고용보험법」에 따른 피보험자", []),
        ("(「개별연장급여 지급을 위한 임금 및 재산기준 고시」)", ["개별연장급여 지급을 위한 임금 및 재산기준 고시"]),
    ],
)
def test_cited_laws(text, expected):
    assert cited_laws(text) == expected
