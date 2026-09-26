"""생활법령 「실업급여」 PDF → Unit 목록.

- 3쪽(목차) 이전은 제외하고, 매 쪽 머리말·쪽 번호를 제거한다.
- 절 제목(글자 크기 11 이상, `2.3.2.` 형식)으로 최하위 절을 나눈다.
- 소제목은 글자 크기가 본문과 같아 들여쓰기(x좌표)와 단독 줄 여부로 판별한다.
- 표는 pdfplumber로 셀을 추출해 행·열 머리글과 함께 직렬화한다.
"""

import re

import pdfplumber

from preprocessing.pdf_to_markdown.common import Line, Unit, make_unit, normalize, page_lines

DOC_ID = "easylaw_unemployment_benefit"
BODY_START_PAGE = 4  # 1쪽 표지, 2쪽 안내문, 3쪽 목차
SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.+)$")
SUB_L1_X = (83.0, 87.0)  # 예: "기초일액의 산정"
SUB_L2_X = (95.5, 98.5)  # 예: "평균임금에 따른 기초일액"
BLOCK_GAP = 17.0  # 줄 간격(약 14.6)보다 크면 새 문단
RIGHT_EDGE = 525.0  # 본문 오른쪽 끝(약 540)
NOT_HEADING_PREFIX = ("√", "※", "Q.", "A.", "<", "-", "·", "*")


def _is_running_text(line: Line) -> bool:
    return line.top < 35 or line.top > 780  # 머리말 "찾기쉬운 생활법령", 쪽 번호 "n / 59"


def _clean(cell) -> str:
    return normalize((cell or "").replace("\n", " "))


def serialize_table(rows: list[list], title: str) -> str:
    """셀 표 → Markdown 표. 병합 셀을 채우고 행·열 머리글은 원문 표현 그대로 둔다."""
    rows = [[_clean(c) for c in r] for r in rows]
    header_rows = [rows[0]]
    for r in rows[1:]:
        if r[0]:
            break
        header_rows.append(r)
    data_rows = rows[len(header_rows) :]

    top = rows[0]
    n_label = 1  # 왼쪽 행 머리글 열 수 (첫 머리글 칸의 가로 병합 범위)
    while n_label < len(top) and top[n_label] == "":
        n_label += 1

    col_headers = []
    for j in range(n_label, len(top)):
        parts = []
        for hr in header_rows:
            k = j
            while k > n_label and not hr[k]:  # 가로 병합된 머리글
                k -= 1
            if hr[k] and hr[k] not in parts:
                parts.append(hr[k])
        col_headers.append(" ".join(parts))

    md = [f"표: {title}", "", "| " + " | ".join([top[0]] + col_headers) + " |", "|" + "---|" * (len(col_headers) + 1)]
    labels = [""] * n_label
    for r in data_rows:
        for j in range(n_label):  # 세로 병합된 행 머리글
            if r[j]:
                labels[j] = r[j]
                labels[j + 1 :] = [""] * (n_label - j - 1)
        cells = [" ".join(dict.fromkeys(l for l in labels if l))] + r[n_label:]
        md.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    return "\n".join(md)


def serialize_tree(rows: list[list], title: str) -> str:
    """분류표(구분 > 종류 > 세부 종류)처럼 값 열 없이 계층만 있는 표 → "상위 > 하위" 목록."""
    rows = [[_clean(c) for c in r] for r in rows]
    header = " > ".join(dict.fromkeys(h for h in rows[0] if h))
    lines, path = [f"표: {title} ({header})", ""], [""] * len(rows[0])
    for r in rows[1:]:
        for j, c in enumerate(r):
            if c:
                path[j] = c
                path[j + 1 :] = [""] * (len(path) - j - 1)
        lines.append("- " + " > ".join(p for p in path if p))
    return "\n".join(lines)


# 표별 직렬화 방식 (쪽 번호 → 방식). 기본은 serialize_table.
TABLE_MODES = {5: serialize_tree}  # 5쪽 실업급여의 종류: 계층 분류표


def _heading_level(block: list[Line]) -> int:
    if len(block) != 1:
        return 0
    line = block[0]
    t = line.text
    if len(t) > 35 or t.startswith(NOT_HEADING_PREFIX) or re.match(r"^\d+[.)]", t):
        return 0
    if re.search(r"(다\.|\.|\))$", t):
        return 0
    if SUB_L1_X[0] <= line.x0 <= SUB_L1_X[1]:
        return 1
    if SUB_L2_X[0] <= line.x0 <= SUB_L2_X[1]:
        return 2
    return 0


def _items(pdf):
    """본문 쪽의 줄과 표를 읽는 순서대로 내보낸다."""
    for pno in range(BODY_START_PAGE, len(pdf.pages) + 1):
        page = pdf.pages[pno - 1]
        tables = page.find_tables()
        boxes = [t.bbox for t in tables]
        items = []
        for line in page_lines(page, pno, pno):
            if _is_running_text(line):
                continue
            if any(b[1] - 2 <= line.top <= b[3] + 2 and b[0] - 2 <= line.x0 <= b[2] for b in boxes):
                continue
            items.append((line.top, "line", line))
        for t in tables:
            items.append((t.bbox[1], "table", (t, pno)))
        for _, kind, obj in sorted(items, key=lambda x: x[0]):
            yield kind, obj


def parse(pdf_path) -> list[Unit]:
    units: list[Unit] = []
    titles = {}  # 절 번호 깊이 → 제목
    section_id, section_path, subpath = None, (), ()
    block: list[Line] = []

    def flush():
        nonlocal block, subpath
        if not block or section_id is None:
            block = []
            return
        level = _heading_level(block)
        if level == 1:
            subpath = (block[0].text,)
        elif level == 2:
            subpath = (subpath[0], block[0].text) if subpath else (block[0].text,)
        units.append(make_unit(DOC_ID, section_id, section_path, subpath, "prose", block, is_heading=level > 0))
        block = []

    with pdfplumber.open(pdf_path) as pdf:
        prev = None
        for kind, obj in _items(pdf):
            if kind == "table":
                flush()
                table, pno = obj
                title = subpath[-1] if subpath else section_path[-1]
                text = TABLE_MODES.get(pno, serialize_table)(table.extract(), title)
                fake = Line(text, 0, table.bbox[1], 0, 0, "", pno, pno)
                units.append(make_unit(DOC_ID, section_id, section_path, subpath, "table", [fake], text=text))
                prev = None
                continue

            line = obj
            m = SECTION_RE.match(line.text)
            if line.size >= 11 and m:
                flush()
                number, title = m.group(1), m.group(2)
                depth = number.count(".") + 1
                titles = {k: v for k, v in titles.items() if k < depth}
                titles[depth] = title
                if depth == 3:  # 최하위 절
                    section_id = number
                    section_path = tuple(titles[k] for k in sorted(titles))
                    subpath = ()
                    units.append(make_unit(DOC_ID, section_id, section_path, (), "prose", [line], is_heading=True))
                prev = None
                continue

            if prev is not None:
                # 앞 줄이 오른쪽 여백까지 찼으면(양쪽 정렬) 이어지는 줄이다. 문단 첫 줄은 줄 간격이 더 넓어
                # 간격만으로는 문단 경계를 판단할 수 없다.
                new_page = line.pdf_page != prev.pdf_page
                gap = new_page or line.top - prev.top > BLOCK_GAP
                heading_like = gap and _heading_level([line]) > 0
                continued = prev.x1 >= RIGHT_EDGE and not line.text.startswith(NOT_HEADING_PREFIX) and not heading_like
                if not continued and gap:
                    flush()
            block.append(line)
            prev = line
        flush()
    return units
