"""검수된 Markdown → canonical text + 구조 기반 청크 + 검수 리포트.

사용법: python -m preprocessing.ingest.build
입력: preprocessing/data/markdown/{doc_id}.md  (PDF에서 1회 변환 후 사람이 검수한 원문)
출력: preprocessing/data/processed/, app/data/processed/
  - {doc_id}.canonical.txt   Gold 근거 좌표의 기준 텍스트 (Markdown에서 주석 줄 제거)
  - app/data/processed/chunks.structure.jsonl   구조 기반 앱 검색 청크
  - chunk_report.md          사람 검수용 청크 목록·분포
"""

import json
import statistics

from app.config import Paths
from preprocessing.ingest.chunker import chunk_markdown, to_dict

DOCS = [  # (doc_id, 제목 접두어용 짧은 이름, 청크 ID 접두어)
    ("easylaw_unemployment_benefit", "생활법령 실업급여", "EL"),
    ("work24_employment_dream_booklet", "취업드림수첩", "BK"),
]


def build() -> dict:
    """문서별 (canonical text, chunks). 파일은 쓰지 않는다."""
    sources = {
        s["id"]: s for s in json.loads((Paths.PREPROCESSING_DATA_DIR / "sources.json").read_text(encoding="utf-8"))
    }
    result = {}
    for doc_id, title, prefix in DOCS:
        md = (Paths.PREPROCESSING_MARKDOWN_DIR / f"{doc_id}.md").read_text(encoding="utf-8")
        result[doc_id] = chunk_markdown(md, doc_id, title, sources[doc_id]["as_of"], prefix)
    return result


def main():
    Paths.PREPROCESSING_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    Paths.APP_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    all_chunks = []
    for doc_id, (canonical, chunks) in build().items():
        (Paths.PREPROCESSING_OUTPUT_DIR / f"{doc_id}.canonical.txt").write_text(canonical, encoding="utf-8")
        all_chunks.extend(chunks)
    with open(Paths.APP_INDEX_DIR / "chunks.structure.jsonl", "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(to_dict(c), ensure_ascii=False) + "\n")
    write_report(all_chunks)
    print(f"{len(all_chunks)} chunks → {Paths.APP_INDEX_DIR}")


def write_report(chunks):
    lines = ["# 청크 검수 리포트", "", "크기는 공백 제외 글자 수.", ""]
    for doc_id, _, _ in DOCS:
        cs = [c for c in chunks if c.doc_id == doc_id]
        n = [c.n_chars for c in cs]
        lines += [
            f"## {doc_id}",
            "",
            f"- 청크 수: {len(cs)} (Q&A {sum(c.content_type == 'qa' for c in cs)}, 표 포함 {sum(c.has_table for c in cs)})",
            f"- 크기: 최소 {min(n)}, 중앙값 {statistics.median(n):.0f}, 평균 {statistics.mean(n):.0f}, 최대 {max(n)}",
            f"- 300자 미만: {sum(x < 300 for x in n)}개, 1500자 초과: {sum(x > 1500 for x in n)}개",
            "",
            "| chunk_id | 쪽 | 글자 | section_path | 시작 |",
            "|---|---|---|---|---|",
        ]
        for c in cs:
            page = f"{c.page_start}" + (f"–{c.page_end}" if c.page_end != c.page_start else "")
            head = (c.question_prefix + " " if c.question_prefix else "") + c.text[:60].replace("\n", " ").replace("|", "/")
            lines.append(f"| {c.chunk_id} | {page} | {c.n_chars} | {' > '.join(c.section_path)} | {head} |")
        lines.append("")
    (Paths.PREPROCESSING_OUTPUT_DIR / "chunk_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
