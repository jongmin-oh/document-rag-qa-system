"""Unit 목록 → canonical text + 구조 기반 청크.

규칙은 docs/chunking_strategy.md 3절을 따른다.
- 청크는 최하위 절(section_id)과 content_type 경계를 넘지 않는다. 표는 항상 단독 청크.
- 절이 SOFT_LIMIT를 넘으면 소제목 1단계 → 2단계 → 문단 순으로 나눈다.
- MIN_CHARS 미만 조각은 같은 절·같은 1단계 소제목·같은 content_type 안에서만 이웃과 합친다.
"""

from dataclasses import asdict, dataclass, field

from app.ingest.common import Unit, cited_laws, nonspace_len

SOFT_LIMIT = 1500  # 공백 제외 글자 수. 분할 판단용 (최종 hard limit는 임베딩 tokenizer로 확정)
MIN_CHARS = 300
UNIT_SEP = "\n\n"


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    parent_section_id: str
    section_path: list[str]
    content_type: str
    text: str  # canonical text의 [char_start, char_end) 구간 그대로
    question_prefix: str  # 분할된 Q&A 조각 앞에 다시 붙이는 원래 질문 (canonical text 밖)
    title_prefix: str  # 조건 C에서만 쓰는 제목 경로 접두어
    char_start: int
    char_end: int
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int
    printed_page_end: int
    n_chars: int  # 공백 제외
    cited_laws: list[str] = field(default_factory=list)
    as_of: str = ""

    def embedding_text(self, with_title: bool) -> str:
        body = f"{self.question_prefix}\n{self.text}" if self.question_prefix else self.text
        return f"{self.title_prefix}\n{body}" if with_title else body


def build_canonical(units: list[Unit]) -> str:
    """Unit 텍스트를 이어 붙이고 각 Unit의 좌표를 기록한다."""
    parts, pos = [], 0
    for i, u in enumerate(units):
        if i:
            parts.append(UNIT_SEP)
            pos += len(UNIT_SEP)
        u.char_start, u.char_end = pos, pos + len(u.text)
        parts.append(u.text)
        pos = u.char_end
    return "".join(parts)


def _size(units: list[Unit]) -> int:
    return sum(nonspace_len(u.text) for u in units)


def _runs(units: list[Unit], key) -> list[list[Unit]]:
    runs = []
    for u in units:
        if runs and key(runs[-1][-1]) == key(u):
            runs[-1].append(u)
        else:
            runs.append([u])
    return runs


def _runs_attaching_headings(units: list[Unit], depth: int) -> list[list[Unit]]:
    """subpath[:depth+1]로 묶되, 제목 단위는 뒤따르는 내용의 묶음에 붙인다."""
    keys, nxt = [], None
    for u in reversed(units):
        k = nxt if (u.is_heading and nxt is not None) else u.subpath[: depth + 1]
        keys.append(k)
        nxt = k
    keys.reverse()
    groups = []
    for u, k in zip(units, keys):
        if groups and groups[-1][0] == k:
            groups[-1][1].append(u)
        else:
            groups.append((k, [u]))
    return [g for _, g in groups]


def _pack(units: list[Unit]) -> list[list[Unit]]:
    groups, cur = [], []
    for u in units:
        if cur and _size(cur) + nonspace_len(u.text) > SOFT_LIMIT:
            groups.append(cur)
            cur = []
        cur.append(u)
    if cur:
        groups.append(cur)
    return groups


def _split(units: list[Unit], depth: int = 0) -> list[list[Unit]]:
    if _size(units) <= SOFT_LIMIT or len(units) == 1:
        return [units]
    max_depth = max(len(u.subpath) for u in units)
    if depth >= max_depth:
        return _pack(units)
    groups = _runs_attaching_headings(units, depth)
    if len(groups) == 1:
        return _split(units, depth + 1)
    return [g for grp in groups for g in _split(grp, depth + 1)]


def _common_subpath(units: list[Unit]) -> tuple[str, ...]:
    first = units[0].subpath
    n = 0
    while n < len(first) and all(len(u.subpath) > n and u.subpath[n] == first[n] for u in units):
        n += 1
    return first[:n]


def _merge_small(groups: list[list[Unit]]) -> list[list[Unit]]:
    out: list[list[Unit]] = []
    for g in groups:
        if out:
            prev = out[-1]
            # 같은 1단계 소제목 안의 형제 조각끼리만 합친다 (1단계 소제목 경계, 표, content_type 경계는 넘지 않음)
            # 절 도입부(소제목 없는 조각: 절 제목, 출처 표기 등)는 뒤따르는 조각과 합칠 수 있다
            preamble = not _common_subpath(prev) and _size(prev) < MIN_CHARS
            same_parent = preamble or _common_subpath(prev)[:1] == _common_subpath(g)[:1]
            same = same_parent and prev[0].content_type == g[0].content_type != "table"
            small = _size(prev) < MIN_CHARS or _size(g) < MIN_CHARS
            if same and small and _size(prev) + _size(g) <= SOFT_LIMIT:
                out[-1] = prev + g
                continue
        out.append(g)
    return out


def chunk_units(units: list[Unit], canonical: str, doc_title: str, as_of: str, id_prefix: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in _runs(units, lambda u: u.section_id):
        groups = []
        # 표는 단독 청크, 나머지는 content_type이 같은 연속 구간끼리 분할
        for run in _runs(section, lambda u: (u.content_type, id(u) if u.content_type == "table" else 0)):
            groups.extend(_merge_small(_split(run)))
        for g in groups:
            first, last = g[0], g[-1]
            # 절 도입부(소제목 없음)가 합쳐진 경우 제목 경로는 나머지 조각의 소제목을 따른다
            sub = _common_subpath([u for u in g if u.subpath] or g)
            path = list(first.section_path) + list(sub)
            text = canonical[first.char_start : last.char_end]
            squash = lambda s: "".join(s.split())
            has_question = bool(first.question) and squash(first.question) in squash(text[: len(first.question) + 40])
            chunks.append(
                Chunk(
                    chunk_id=f"{id_prefix}-{len(chunks):04d}",
                    doc_id=first.doc_id,
                    parent_section_id=first.section_id,
                    section_path=path,
                    content_type=first.content_type,
                    text=text,
                    question_prefix="" if (not first.question or has_question) else f"Q. {first.question}",
                    title_prefix=f"[{doc_title} | {as_of} 기준] " + " > ".join(path),
                    char_start=first.char_start,
                    char_end=last.char_end,
                    pdf_page_start=first.pdf_pages[0],
                    pdf_page_end=last.pdf_pages[1],
                    printed_page_start=first.printed_pages[0],
                    printed_page_end=last.printed_pages[1],
                    n_chars=nonspace_len(text),
                    cited_laws=cited_laws(text),
                    as_of=as_of,
                )
            )
    return chunks


def to_dict(chunk: Chunk) -> dict:
    return asdict(chunk)
