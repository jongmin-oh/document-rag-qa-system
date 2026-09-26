"""PDF 추출 공통 자료구조와 유틸리티."""

import re
from collections import Counter
from dataclasses import dataclass



@dataclass
class Line:
    text: str
    x0: float
    top: float
    x1: float
    size: float
    font: str
    pdf_page: int
    printed_page: int


@dataclass
class Unit:
    """구조상 더 쪼개지 않는 최소 단위(문단, 소제목, 표, Q&A 문단 등)."""

    doc_id: str
    section_id: str  # 최하위 절 또는 Q&A 번호. 청크는 이 경계를 넘지 않는다
    section_path: tuple[str, ...]  # 문서 내 절 제목 경로
    subpath: tuple[str, ...]  # 절 안의 소제목 경로
    content_type: str  # prose | qa | table | notice
    text: str
    pdf_pages: tuple[int, int]
    printed_pages: tuple[int, int]
    question: str = ""  # Q&A 단위일 때 원래 질문 (분할 시 앞에 다시 붙임)
    is_heading: bool = False  # 제목만 있는 단위
    line_pages: tuple[int, ...] = ()  # 줄별 인쇄 쪽 번호 (Markdown 쪽 표시용)


def page_lines(page, pdf_page: int, printed_page: int, x_offset: float = 0.0, infer_spaces: bool = False) -> list[Line]:
    """infer_spaces=True면 PDF의 공백 글자를 버리고 글자 간격으로 띄어쓰기를 다시 판단한다.
    (수첩은 공백 글자가 다음 글자와 겹쳐 찍혀 "실 업인정"처럼 잘못 띄어지는 경우가 있다)"""
    if infer_spaces:
        page = page.filter(lambda o: not (o.get("object_type") == "char" and o.get("text") == " "))
    lines = []
    for ln in page.extract_text_lines(x_tolerance=1.0 if infer_spaces else 1.5):
        text = ln["text"].strip()
        if not text:
            continue
        size = Counter(round(c["size"], 1) for c in ln["chars"]).most_common(1)[0][0]
        font = Counter(c["fontname"].split("+")[-1] for c in ln["chars"]).most_common(1)[0][0]
        lines.append(Line(text, ln["x0"] - x_offset, ln["top"], ln["x1"] - x_offset, size, font, pdf_page, printed_page))
    return lines


def nonspace_len(text: str) -> int:
    return len(re.sub(r"\s", "", text))


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def make_unit(
    doc_id, section_id, section_path, subpath, content_type, lines: list[Line], question="", text=None, is_heading=False
) -> Unit:
    return Unit(
        doc_id=doc_id,
        section_id=section_id,
        section_path=tuple(section_path),
        subpath=tuple(subpath),
        content_type=content_type,
        text=text if text is not None else "\n".join(l.text for l in lines),
        pdf_pages=(lines[0].pdf_page, lines[-1].pdf_page),
        printed_pages=(lines[0].printed_page, lines[-1].printed_page),
        question=question,
        is_heading=is_heading,
        line_pages=tuple(l.printed_page for l in lines) if text is None else (lines[0].printed_page,) * (text.count("\n") + 1),
    )
