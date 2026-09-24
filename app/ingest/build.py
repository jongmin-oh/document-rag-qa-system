"""Corpus PDF → canonical text + 구조 기반 청크 + 검수 리포트.

사용법: python -m app.ingest.build
출력: app/data/processed/
  - {doc_id}.canonical.txt   Gold 근거 좌표의 기준 텍스트
  - chunks.structure.jsonl   구조 기반 청크 (조건 B/C 공용, C는 title_prefix 사용)
  - chunk_report.md          사람 검수용 청크 목록·분포
"""

import json
import statistics
from pathlib import Path

from app.ingest import booklet, easylaw
from app.ingest.chunker import build_canonical, chunk_units, to_dict

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "processed"
DOCS = [
    # (모듈, 파일, 제목 접두어용 짧은 이름, 청크 ID 접두어)
    (easylaw, "easylaw_unemployment_benefit.pdf", "생활법령 실업급여", "EL"),
    (booklet, "work24_employment_dream_booklet.pdf", "취업드림수첩", "BK"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {s["id"]: s for s in json.loads((DATA / "sources.json").read_text(encoding="utf-8"))}
    all_chunks = []
    for module, filename, title, prefix in DOCS:
        units = module.parse(DATA / "raw" / filename)
        canonical = build_canonical(units)
        (OUT / f"{module.DOC_ID}.canonical.txt").write_text(canonical, encoding="utf-8")
        chunks = chunk_units(units, canonical, title, sources[module.DOC_ID]["as_of"], prefix)
        assert all(canonical[c.char_start : c.char_end] == c.text for c in chunks)
        all_chunks.extend(chunks)

    with open(OUT / "chunks.structure.jsonl", "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(to_dict(c), ensure_ascii=False) + "\n")
    write_report(all_chunks)
    print(f"{len(all_chunks)} chunks → {OUT}")


def write_report(chunks):
    lines = ["# 청크 검수 리포트", "", "크기는 공백 제외 글자 수.", ""]
    for doc_id in dict.fromkeys(c.doc_id for c in chunks):
        cs = [c for c in chunks if c.doc_id == doc_id]
        n = [c.n_chars for c in cs]
        types = {t: sum(c.content_type == t for c in cs) for t in dict.fromkeys(c.content_type for c in cs)}
        lines += [
            f"## {doc_id}",
            "",
            f"- 청크 수: {len(cs)} ({', '.join(f'{k} {v}' for k, v in types.items())})",
            f"- 크기: 최소 {min(n)}, 중앙값 {statistics.median(n):.0f}, 평균 {statistics.mean(n):.0f}, 최대 {max(n)}",
            f"- 300자 미만: {sum(x < 300 for x in n)}개, 1500자 초과: {sum(x > 1500 for x in n)}개",
            "",
            "| chunk_id | type | 쪽 | 글자 | section_path | 시작 |",
            "|---|---|---|---|---|---|",
        ]
        for c in cs:
            page = f"{c.printed_page_start}" + (f"–{c.printed_page_end}" if c.printed_page_end != c.printed_page_start else "")
            head = (c.question_prefix + " " if c.question_prefix else "") + c.text[:60].replace("\n", " ").replace("|", "/")
            lines.append(f"| {c.chunk_id} | {c.content_type} | {page} | {c.n_chars} | {' > '.join(c.section_path)} | {head} |")
        lines.append("")
    tables = [c for c in chunks if c.content_type == "table"]
    lines += ["## 표 직렬화 결과 (원문 대조용)", ""]
    for c in tables:
        lines += [f"### {c.chunk_id} ({c.doc_id} {c.printed_page_start}쪽)", "", "```", c.text, "```", ""]
    (OUT / "chunk_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
