"""취업드림수첩 e북 PDF → Unit 목록.

- PDF 한 장에 책자 2쪽이 좌우로 있어 반씩 잘라 읽는다(1장·35장은 한 쪽).
- 인쇄 쪽 번호: 왼쪽 = 2*(장-1), 오른쪽 = 2*(장-1)+1. 쪽 하단 번호로 검증한다.
- 장별 역할(아래 PAGE_ROLES)에 따라 본문·표·서식 안내문을 가르고, 빈 서식·달력·목차는 제외한다.
- 본문(22–39쪽 Q&A 등)은 매 쪽 상단의 섹션 제목과 항목 제목(글꼴로 판별)으로 구조를 잡는다.
  번호 없는 항목 제목은 소제목 그룹(예: "직업능력개발 지원")으로 두고, 뒤따르는 번호 항목의 경로에 넣는다.
- 섹션·그룹 도입부가 짧으면 독립 청크로 두지 않고 바로 뒤 첫 항목에 붙인다.
- 문의처 상자는 여러 쪽에 문구만 조금 다르게 반복되므로 마지막(68쪽) 것 하나만 남긴다.
- 자동 추출로 구조가 깨지는 표는 app/ingest/curated.py의 검수된 직렬화로 대체한다.
"""

import re

import pdfplumber

from tools.pdf_to_markdown.common import Line, Unit, make_unit, nonspace_len, normalize, page_lines
from tools.pdf_to_markdown.curated import BOOKLET as CURATED

DOC_ID = "work24_employment_dream_booklet"
FOOTER_TOP = 390  # 쪽 번호
SECTION_SHORT = {
    "구직급여 수급 중 유의사항 Q&A": "qa",
    "고용24 홈페이지 활용하기": "work24",
    "실업급여 제도에 대해 좀 더 알아보기": "system",
    "실업급여 부정수급이란": "fraud",
    "취업지원 프로그램": "support",
}
CONTACT_BOX = "실업급여에 대해 궁금한 점이 있다면?"
CARRY_MAX = 300  # 이보다 짧은 섹션·그룹 도입부는 다음 항목에 붙인다
SENTENCE_END = re.compile(r"(니다|세요|하세요|바랍니다|요)[.!)]?\s*$|니다\.")

# (PDF 장, 반쪽) → 역할. 반쪽: 0=왼쪽, 1=오른쪽. 여기에 없는 12–33장은 "body".
PAGE_ROLES = {
    (1, 0): ("skip", "표지"),
    (2, 0): ("skip", "인사말"),
    (2, 1): ("prose", "고용보험 수급자격증 유의사항"),
    (3, 0): ("notice", "수급자격증 붙이는 곳"),
    (3, 1): ("table", "실업인정 유형별 재취업활동 최소 횟수 및 인정 범위"),
    **{(p, h): ("notice", "실업인정 기록표·구직활동내역 서식") for p in range(4, 9) for h in (0, 1)},
    (9, 0): ("skip", "근로·소득 기록 달력"),
    (9, 1): ("skip", "근로·소득 기록 달력"),
    (10, 0): ("skip", "근로·소득 기록 달력"),
    (10, 1): ("skip", "근로·소득 기록 달력"),
    (11, 0): ("prose", "구직급여 수급자 여러분께"),
    (11, 1): ("skip", "목차"),
    (12, 0): ("skip", "Q&A 목차"),
    (12, 1): ("skip", "Q&A 목차"),
    (34, 0): ("notice", "면접사실 확인서 서식"),
    (34, 1): ("skip", "뒤표지(5쪽 재취업활동 기준 표와 중복)"),
    (35, 0): ("notice", "문의처"),
}


def _is_item_heading(line: Line) -> bool:
    return 9.3 <= line.size <= 9.7 and ("Lucky" in line.font or "Elice" in line.font)


def _is_section_title(line: Line) -> bool:
    return line.size >= 11.5 and "Gmarket" in line.font and line.top < 70


def _is_bullet(text: str) -> bool:
    return text.startswith(("•", "※", "*", "☞"))


def _halves(pdf):
    for pno, page in enumerate(pdf.pages, start=1):
        page = page.dedupe_chars()  # 굵은 글씨를 겹쳐 찍은 글자 제거
        w = page.width
        if w < 400:
            yield pno, 0, page, 0.0, (1 if pno == 1 else 2 * (pno - 1))
            continue
        for half, x0 in ((0, 0.0), (1, w / 2)):
            crop = page.crop((x0, 0, x0 + w / 2, page.height))
            yield pno, half, crop, x0, 2 * (pno - 1) + half


def _split_blocks(lines: list[Line]) -> list[list[Line]]:
    """글머리표(•, ※ 등)로 시작하는 줄에서 문단을 나눈다."""
    blocks, cur = [], []
    for line in lines:
        if cur and _is_bullet(line.text):
            blocks.append(cur)
            cur = []
        cur.append(line)
    if cur:
        blocks.append(cur)
    return blocks


def parse(pdf_path) -> list[Unit]:
    units: list[Unit] = []
    seen_notices: set[str] = set()
    contact: list[Line] = []  # 마지막으로 본 문의처 상자
    section = None
    group_title = ""  # 번호 없는 항목 제목 (소제목 그룹)
    item_id, item_title = None, ""
    body: list[Line] = []
    counters: dict[str, int] = {}

    def emit_notice(lines: list[Line], label: str):
        """서식 장에서 안내 문장만 남긴다. 서식 머리글·기입 예시는 문장이 아니므로 버린다.
        여러 장에 반복되는 안내문은 정규화한 텍스트 기준으로 한 번만 남긴다."""
        kept, open_sentence = [], False
        for i, line in enumerate(lines):
            if open_sentence or _is_bullet(line.text) or SENTENCE_END.search(line.text):
                # 문장이 바로 윗줄에서 시작된 경우 윗줄도 살린다 (서식 머리글은 안내문과 멀리 떨어져 있다)
                p = lines[i - 1] if i else None
                if p and p not in kept and 0 < line.top - p.top <= 12 and not p.text.rstrip().endswith((".", "!", ")")):
                    kept.append(p)
                kept.append(line)
                open_sentence = not line.text.rstrip().endswith((".", "!", ")"))
        blocks, cur = [], []
        for line in kept:
            if cur and _is_bullet(line.text):
                blocks.append(cur)
                cur = []
            cur.append(line)
            if line.text.rstrip().endswith((".", "!")):
                blocks.append(cur)
                cur = []
        if cur:
            blocks.append(cur)
        for block in blocks:
            key = normalize("".join(l.text for l in block)).replace(" ", "")
            if len(key) < 10 or key in seen_notices:
                continue
            seen_notices.add(key)
            units.append(make_unit(DOC_ID, "notice-form", ("서식 안내문", label), (), "notice", block))

    def carryable() -> bool:
        """현재 모인 내용이 섹션·그룹 도입부이고 짧으면 다음 항목에 붙인다."""
        is_intro = item_id is None or item_id.startswith("g")
        return bool(body) and is_intro and nonspace_len(" ".join(l.text for l in body)) < CARRY_MAX

    def flush_item():
        nonlocal body
        if not body or section is None:
            body = []
            return
        short = SECTION_SHORT[section]
        ctype = "qa" if short == "qa" else "prose"
        sid = f"{short}-{item_id}" if item_id else f"{short}-intro"
        path = tuple(p for p in (section, group_title, item_title) if p)
        question = item_title if ctype == "qa" else ""
        blocks = _split_blocks(body)
        while len(blocks) > 1 and nonspace_len(" ".join(l.text for l in blocks[0])) < 60:
            blocks[1] = blocks[0] + blocks[1]  # 제목·짧은 도입 문단은 다음 문단과 합친다
            blocks.pop(0)
        for block in blocks:
            units.append(make_unit(DOC_ID, sid, path, (), ctype, block, question=question))
        body = []

    with pdfplumber.open(pdf_path) as pdf:
        for pno, half, page, x0, printed in _halves(pdf):
            lines = page_lines(page, pno, printed, x_offset=x0, infer_spaces=True)
            footer = [l for l in lines if l.top > FOOTER_TOP and l.text.isdigit()]
            assert not footer or int(footer[0].text) == printed, (pno, half, footer[0].text, printed)
            lines = [l for l in lines if l not in footer]

            role, label = PAGE_ROLES.get((pno, half), ("body", ""))
            if role != "body":
                flush_item()
            if role == "skip" or not lines:
                continue
            if role == "notice":
                if label == "문의처":
                    contact = lines
                else:
                    emit_notice(lines, label)
                continue
            if role in ("prose", "table"):
                sid = "front-" + ("table" if role == "table" else f"p{printed}")
                units.append(make_unit(DOC_ID, sid, ("머리말", label), (), role, lines))
                continue

            # 본문: 섹션 제목 → 항목 제목 → 내용
            titles = [l for l in lines if _is_section_title(l)]
            if titles:
                name = normalize(" ".join(l.text for l in titles if l.size >= 13.5) or titles[0].text)
                if name in SECTION_SHORT and name != section:
                    flush_item()
                    section, group_title, item_id, item_title = name, "", None, ""
                lines = [l for l in lines if l not in titles]

            if any(l.text.startswith(CONTACT_BOX) for l in lines):  # 섹션 표지의 문의처 상자
                k = next(i for i, l in enumerate(lines) if l.text.startswith(CONTACT_BOX))
                contact = lines[k:]
                lines = [l for l in lines[:k] if not re.match(r"^0\d\.\s", l.text)]  # 섹션 표지의 소목차

            i = 0
            while i < len(lines):
                line = lines[i]
                if not _is_item_heading(line):
                    body.append(line)
                    i += 1
                    continue
                heads = [line]
                while i + 1 < len(lines) and _is_item_heading(lines[i + 1]) and not re.match(r"^\d", lines[i + 1].text):
                    i += 1
                    heads.append(lines[i])
                text = normalize(" ".join(h.text for h in heads))
                carried = body if carryable() else []
                if not carried:
                    flush_item()
                m = re.match(r"^(\d+(?:-\d+)?)\.\s*(.+)$", text)
                if m:
                    item_id, item_title = m.group(1), m.group(2)
                else:  # 번호 없는 제목: 소제목 그룹
                    short = SECTION_SHORT[section]
                    counters[short] = counters.get(short, 0) + 1
                    group_title, item_id, item_title = text, f"g{counters[short]}", ""
                body = carried + heads
                i += 1
        flush_item()
    if contact:  # 마지막 문의처 상자 하나만 남긴다
        units.append(make_unit(DOC_ID, "notice-contact", ("서식 안내문", "문의처"), (), "notice", contact))
    return apply_curated(units)


def apply_curated(units: list[Unit]) -> list[Unit]:
    """검수된 Markdown이 있는 항목은 자동 추출 결과를 대체한다.
    항목 제목 줄 앞에 붙은 섹션 도입 문장은 그대로 보존한다."""
    out: list[Unit] = []
    for u in units:
        if u.section_id not in CURATED:
            out.append(u)
            continue
        if any(x.section_id == u.section_id for x in out):
            continue
        lines, pages = u.text.split("\n"), list(u.line_pages)
        k = next((i + 1 for i, s in enumerate(lines) if re.match(r"^\d+\.\s", s)), 0)  # 항목 제목 줄까지 보존
        start, md = CURATED[u.section_id]
        md_lines = md.split("\n")
        text = "\n".join(lines[:k] + md_lines)
        line_pages = tuple(pages[:k] + [start] * len(md_lines))
        out.append(Unit(DOC_ID, u.section_id, u.section_path, (), "table", text, u.pdf_pages, (line_pages[0], line_pages[-1]), line_pages=line_pages))
    return out
