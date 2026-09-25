"""검수된 Markdown → canonical text + 구조 기반 청크.

청킹 규칙 (decision/chunking_strategy.md):
1. Markdown 제목(#)으로 트리를 만든다.
2. 제목 아래 전체(하위 제목 포함)가 SOFT_LIMIT 이하면 하나의 청크로 둔다.
   넘으면 하위 제목으로 내려가 같은 규칙을 반복한다.
   하위 제목이 없는데도 길면 문단(빈 줄 경계) 단위로 SOFT_LIMIT까지 채워 나눈다. 문단과 표는 쪼개지 않는다.
3. 병합: 제목만 있는 조각은 다음 조각에 붙인다. MIN_CHARS 미만 조각은 같은 상위 제목 아래의
   이웃 조각과 합친다. 단 Q&A(Q로 시작하는 제목)끼리는 합치지 않는다.

canonical text = Markdown에서 주석 줄(<!-- p.N --> 쪽 표시 등)을 뺀 텍스트.
모든 청크는 canonical text의 연속 구간이고, Gold 근거도 같은 좌표를 쓴다.
"""

import bisect
import re
from dataclasses import asdict, dataclass, field

from app.tasks.ingest.laws import cited_laws

SOFT_LIMIT = 1500  # 공백 제외 글자 수
MIN_CHARS = 300
PAGE = re.compile(r"^<!-- p\.(\d+) -->$")
COMMENT = re.compile(r"^<!--.*-->$")
HEADING = re.compile(r"^(#{1,6}) (.+)$")
QA_TITLE = re.compile(r"^Q\d")


def size(text: str) -> int:
    return len(re.sub(r"\s", "", text))


@dataclass
class Block:  # 빈 줄로 구분되는 문단·표·목록, 또는 제목 한 줄
    start: int
    end: int
    level: int = 0  # 제목이면 1–6
    title: str = ""


@dataclass
class Node:  # 제목 하나와 그 아래 내용
    title: str
    level: int
    blocks: list[Block] = field(default_factory=list)  # 자기 제목 줄 + 첫 하위 제목 전까지의 본문
    children: list["Node"] = field(default_factory=list)
    start: int = 0
    end: int = 0


@dataclass
class Span:  # 청크 후보 구간
    start: int
    end: int
    path: list[str]
    question_prefix: str = ""


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    section_path: list[str]
    content_type: str  # qa | prose
    has_table: bool
    text: str  # canonical text[char_start:char_end]
    question_prefix: str  # 나뉜 Q&A의 뒤쪽 조각에 다시 붙이는 질문 (canonical text 밖)
    title_prefix: str  # 조건 C에서만 쓰는 "[문서 | 기준일] 제목 > 경로"
    char_start: int
    char_end: int
    page_start: int
    page_end: int
    n_chars: int
    cited_laws: list[str]
    as_of: str


def load_markdown(md: str) -> tuple[str, list[tuple[int, int]]]:
    """주석 줄을 뺀 canonical text와 (시작 위치, 쪽) 목록을 만든다."""
    out, pages, pos, page = [], [], 0, 0
    for line in md.split("\n"):
        m = PAGE.match(line)
        if m:
            page = int(m.group(1))
            continue
        if COMMENT.match(line):
            continue
        if not pages or pages[-1][1] != page:
            pages.append((pos, page))
        out.append(line + "\n")
        pos += len(line) + 1
    return "".join(out), pages


def split_blocks(text: str) -> list[Block]:
    blocks, start, pos = [], None, 0
    for line in text.split("\n"):
        end = pos + len(line)
        h = HEADING.match(line)
        if h or not line.strip():  # 제목 줄과 빈 줄은 앞 문단을 닫는다
            if start is not None:
                blocks.append(Block(start, pos - 1))
                start = None
            if h:
                blocks.append(Block(pos, end, len(h.group(1)), h.group(2).strip()))
        elif start is None:
            start = pos
        pos = end + 1
    if start is not None:
        blocks.append(Block(start, len(text.rstrip("\n"))))
    return blocks


def build_tree(blocks: list[Block]) -> Node:
    root = Node("", 0)
    stack = [root]
    for b in blocks:
        if b.level:
            while stack[-1].level >= b.level:
                stack.pop()
            node = Node(b.title, b.level, [b], start=b.start)
            stack[-1].children.append(node)
            stack.append(node)
        else:  # 본문은 가장 최근에 열린(가장 깊은) 제목에 속한다
            stack[-1].blocks.append(b)
        for n in stack:  # 조상 노드의 끝 위치를 늘린다
            n.end = max(n.end, b.end)
    return root


def pack(blocks: list[Block], text: str, path: list[str]) -> list[Span]:
    """연속된 블록을 SOFT_LIMIT까지 채워 묶는다. 블록 하나는 쪼개지 않는다."""
    spans, cur = [], []
    for b in blocks:
        if cur and size(text[cur[0].start : b.end]) > SOFT_LIMIT:
            spans.append(Span(cur[0].start, cur[-1].end, path))
            cur = []
        cur.append(b)
    if cur:
        spans.append(Span(cur[0].start, cur[-1].end, path))
    return spans


def split_node(node: Node, text: str, path: list[str]) -> list[Span]:
    if node.level and size(text[node.start : node.end]) <= SOFT_LIMIT:
        return [Span(node.start, node.end, path)]
    spans = pack(node.blocks, text, path)
    if QA_TITLE.match(node.title):  # 나뉜 Q&A는 뒤쪽 조각에도 질문을 붙인다
        for s in spans[1:]:
            s.question_prefix = node.title
    for child in node.children:
        spans += split_node(child, text, path + [child.title])
    return spans


def is_heading_only(span: Span, text: str) -> bool:
    return all(HEADING.match(l) or not l.strip() for l in text[span.start : span.end].split("\n"))


def mergeable(a: Span, b: Span, text: str) -> bool:
    if any(QA_TITLE.match(t) for t in a.path + b.path):
        return False
    # 같은 제목의 조각 / 상위 도입부와 첫 하위 항목 / 같은 상위 제목 아래 형제 (최상위 섹션끼리는 제외)
    related = a.path == b.path or a.path == b.path[:-1] or (a.path[:-1] == b.path[:-1] and len(a.path) > 1)
    small = size(text[a.start : a.end]) < MIN_CHARS or size(text[b.start : b.end]) < MIN_CHARS
    return related and small and size(text[a.start : b.end]) <= SOFT_LIMIT


def merge(spans: list[Span], text: str) -> list[Span]:
    out: list[Span] = []
    for s in spans:
        if out and is_heading_only(out[-1], text):  # 제목만 있는 조각은 다음 조각에 붙인다
            out[-1] = Span(out[-1].start, s.end, s.path, s.question_prefix)
        elif out and not is_heading_only(s, text) and mergeable(out[-1], s, text):
            prev = out[-1]
            # 상위 도입부 + 첫 하위 항목이면 하위 경로를, 형제끼리면 공통 상위 경로를 쓴다
            path = s.path if prev.path == s.path[:-1] else [x for x, y in zip(prev.path, s.path) if x == y]
            out[-1] = Span(prev.start, s.end, path)
        else:
            out.append(s)
    return out


def page_at(pages: list[tuple[int, int]], pos: int) -> int:
    """load_markdown의 (시작 위치, 쪽) 목록에서 pos가 속한 인쇄 쪽."""
    return pages[bisect.bisect_right([p for p, _ in pages], pos) - 1][1]


def to_chunks(text: str, pages, spans: list[Span], doc_id: str, doc_title: str, as_of: str, id_prefix: str) -> list[Chunk]:
    chunks = []
    for s in spans:
        body = text[s.start : s.end]
        chunks.append(
            Chunk(
                chunk_id=f"{id_prefix}-{len(chunks):04d}",
                doc_id=doc_id,
                section_path=s.path,
                content_type="qa" if any(QA_TITLE.match(t) for t in s.path) else "prose",
                has_table=any(l.startswith("|") for l in body.split("\n")),
                text=body,
                question_prefix=f"Q. {s.question_prefix}" if s.question_prefix else "",
                title_prefix=f"[{doc_title} | {as_of} 기준] " + " > ".join(s.path),
                char_start=s.start,
                char_end=s.end,
                page_start=page_at(pages, s.start),
                page_end=page_at(pages, s.end - 1),
                n_chars=size(body),
                cited_laws=cited_laws(body),
                as_of=as_of,
            )
        )
    return chunks


def chunk_markdown(md: str, doc_id: str, doc_title: str, as_of: str, id_prefix: str) -> tuple[str, list[Chunk]]:
    text, pages = load_markdown(md)
    spans = merge(split_node(build_tree(split_blocks(text)), text, []), text)
    return text, to_chunks(text, pages, spans, doc_id, doc_title, as_of, id_prefix)


def chunk_fixed(md: str, doc_id: str, doc_title: str, as_of: str, id_prefix: str, target: int) -> list[Chunk]:
    """조건 A(비교 기준): 제목·문단 구조를 무시하고 공백 제외 target자마다 자른다.

    단어 중간에서 자르지 않도록 target자에 이른 뒤 처음 나오는 공백에서 끊는다. 청크는 canonical text를 빈틈없이 나눈다.
    """
    text, pages = load_markdown(md)
    spans, start, n = [], 0, 0
    for i, ch in enumerate(text):
        if not ch.isspace():
            n += 1
        elif n >= target:
            spans.append(Span(start, i, []))
            start, n = i, 0
    if n:
        spans.append(Span(start, len(text), []))
    else:
        spans[-1].end = len(text)
    return to_chunks(text, pages, spans, doc_id, doc_title, as_of, id_prefix)


def to_dict(chunk: Chunk) -> dict:
    return asdict(chunk)
