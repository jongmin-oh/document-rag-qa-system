"""PDF → Markdown 초안 생성 (1회성 도구).

사용법: python -m preprocessing.pdf_to_markdown.export
출력: preprocessing/data/markdown/{doc_id}.md

생성된 Markdown은 사람이 원문 PDF와 대조해 검수·수정한 뒤 커밋한다(수첩 표 3개는 이 단계에서 직접 옮겨 적었다).
다시 실행하면 검수한 내용이 덮어써지므로 PDF가 개정됐을 때만 실행한다.
이후 파이프라인(preprocessing/ingest)은 PDF가 아니라 이 Markdown만 읽는다.
`<!-- p.N -->`은 인쇄 쪽 번호 표시로, 다음 줄부터 N쪽이라는 뜻이다.
"""

from pathlib import Path

from preprocessing.pdf_to_markdown import booklet, easylaw

DATA = Path(__file__).resolve().parents[1] / "data"
RAW = DATA / "raw"
OUT = DATA / "markdown"


def squash(s: str) -> str:
    return "".join(s.split())


class Writer:
    def __init__(self):
        self.out: list[str] = []
        self.path: tuple[str, ...] = ()
        self.page = None

    def mark(self, page: int):
        if page != self.page:
            self.out.append(f"<!-- p.{page} -->")
            self.page = page

    def headings(self, path: tuple[str, ...], page: int):
        common = 0
        while common < min(len(path), len(self.path)) and path[common] == self.path[common]:
            common += 1
        for level in range(common, len(path)):
            self.mark(page)
            self.out += [f"{'#' * (level + 1)} {path[level]}", ""]
        self.path = path

    def text(self, lines: list[str], pages: list[int]):
        if not lines:
            return
        for line, page in zip(lines, pages):
            self.mark(page)
            self.out.append(line)
        self.out.append("")


def find_lines(lines: list[str], target: str) -> tuple[int, int] | None:
    """여러 줄에 걸친 제목을 찾는다 (공백 무시)."""
    target = squash(target)
    for i in range(len(lines)):
        acc = ""
        for j in range(i, min(i + 4, len(lines))):
            acc += squash(lines[j])
            if acc == target:
                return i, j + 1
            if not target.startswith(acc):
                break
    return None


def export_easylaw() -> str:
    w = Writer()
    for u in easylaw.parse(RAW / "easylaw_unemployment_benefit.pdf"):
        n = u.section_id.split(".")
        base = (f"{n[0]}. {u.section_path[0]}", f"{n[0]}.{n[1]}. {u.section_path[1]}", f"{u.section_id}. {u.section_path[2]}")
        path = base + u.subpath
        w.headings(path, u.line_pages[0])
        if not u.is_heading:
            w.text(u.text.split("\n"), list(u.line_pages))
    return "\n".join(w.out)


def booklet_path(u) -> tuple[str, ...]:
    sid, sp = u.section_id, u.section_path
    if sid.startswith("front-"):
        return ("머리말", sp[1])
    if sid == "notice-form":
        return ("머리말", f"{sp[1]} 안내문") if u.printed_pages[0] <= 20 else (f"{sp[1]} 안내문",)
    if sid == "notice-contact":
        return ("문의처",)
    item = sid.split("-", 1)[1]
    if item == "intro":
        return (sp[0],)
    if item.startswith("g"):
        return sp[:2]
    prefix = "Q" if sid.startswith("qa-") else ""
    return sp[:-1] + (f"{prefix}{item}. {sp[-1]}",)


def export_booklet() -> str:
    w = Writer()
    seen = set()
    for u in booklet.parse(RAW / "work24_employment_dream_booklet.pdf"):
        path = booklet_path(u)
        lines, pages = u.text.split("\n"), list(u.line_pages)
        first = u.section_id not in seen
        seen.add(u.section_id)
        item = u.section_id.split("-", 1)[-1]
        if first and u.section_id.split("-")[0] in booklet.SECTION_SHORT.values() and item != "intro":
            # 본문에 섞여 있는 그룹·항목 제목 줄은 Markdown 제목으로 옮기고 본문에서 뺀다
            drop = set()
            for title in path[1:]:
                span = find_lines(lines, title.split(". ", 1)[-1] if title[0] in "Q0123456789" else title)
                if span is None and title[0] in "Q0123456789":
                    span = find_lines(lines, title.lstrip("Q"))
                if span:
                    drop.update(range(*span))
            item_span = find_lines(lines, path[-1].lstrip("Q")) if not item.startswith("g") else None
            cut = item_span[0] if item_span else 0
            intro = [(l, p) for k, (l, p) in enumerate(zip(lines[:cut], pages[:cut])) if k not in drop]
            rest = [(l, p) for k, (l, p) in enumerate(zip(lines, pages)) if k >= cut and k not in drop]
            if intro:  # 항목 제목보다 앞에 있던 섹션·그룹 도입 문장
                w.headings(path[:-1], intro[0][1])
                w.text([l for l, _ in intro], [p for _, p in intro])
            lines, pages = [l for l, _ in rest], [p for _, p in rest]
        w.headings(path, pages[0] if pages else u.line_pages[0])
        w.text(lines, pages)
    return "\n".join(w.out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for doc_id, fn in (("easylaw_unemployment_benefit", export_easylaw), ("work24_employment_dream_booklet", export_booklet)):
        (OUT / f"{doc_id}.md").write_text(fn().rstrip() + "\n", encoding="utf-8")
        print(f"→ {OUT / doc_id}.md")


if __name__ == "__main__":
    main()
