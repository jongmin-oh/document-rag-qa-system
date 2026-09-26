"""Gold Set 원본(YAML) → 근거 좌표가 붙은 Gold Set(JSONL).

사용법: python -m evaluation.gold.build
입력: evaluation/data/gold/gold_set.yaml  (사람이 작성·검수. 근거는 문서 원문 인용)
출력: evaluation/data/processed/gold_set.jsonl

근거 인용문(quote)을 canonical text에서 찾아 char_start/char_end와 인쇄 쪽을 붙인다.
- 공백·줄바꿈 차이와 한자 호환 문자(離 U+F9EA ↔ 離 U+96E2) 차이는 무시하고, 문서 안에서 정확히 한 번 나와야 한다.
- 긴 구간은 "시작 문구 ... 끝 문구"로 적는다. 끝 문구는 시작 문구 뒤 첫 위치를 쓴다.
- alt: 같은 내용을 다른 곳에서도 말하는 근거. 평가에서는 본 근거와 alt 중 하나만 회수해도 회수로 본다.
"""

import json
import re
import unicodedata

import yaml

from app.config import Paths
from preprocessing.ingest.build import DOCS
from preprocessing.ingest.chunker import load_markdown, page_at

ANSWERABILITY = {"full", "partial", "none"}  # 문서로 전부 답함 | 일부만 답함 | 답할 수 없음(거부해야 함)
QUESTION_TYPES = {"factoid", "procedural", "multi_hop", "summary", "unanswerable"}
GAP = " ... "


def fold(s: str) -> str:
    """글자 수가 바뀌지 않는 NFKC 정규화. 원문 좌표를 그대로 쓰기 위해 한 글자 → 한 글자 변환만 적용한다."""
    return "".join(n if len(n := unicodedata.normalize("NFKC", c)) == 1 else c for c in s)


def pattern(quote: str) -> str:
    return r"\s+".join(map(re.escape, fold(quote).split()))


def locate(text: str, quote: str) -> tuple[int, int]:
    head, _, tail = quote.partition(GAP)
    found = [m.span() for m in re.finditer(pattern(head), text)]
    if len(found) != 1:
        raise ValueError(f"인용문이 {len(found)}번 나옴 (1번이어야 함): {head[:50]}")
    start, end = found[0]
    if tail:
        m = re.compile(pattern(tail)).search(text, end)
        if not m:
            raise ValueError(f"끝 문구를 시작 문구 뒤에서 찾지 못함: {tail[:50]}")
        end = m.end()
    return start, end


def resolve(ev: dict, docs: dict) -> dict:
    text, pages = docs[ev["doc_id"]]
    start, end = locate(text, ev["quote"])
    return {
        "doc_id": ev["doc_id"],
        "quote": ev["quote"],
        "char_start": start,
        "char_end": end,
        "page_start": page_at(pages, start),
        "page_end": page_at(pages, end - 1),
    }


def build() -> list[dict]:
    docs = {}
    for d, _, _ in DOCS:
        text, pages = load_markdown((Paths.PREPROCESSING_MARKDOWN_DIR / f"{d}.md").read_text(encoding="utf-8"))
        docs[d] = (fold(text), pages)
    items = yaml.safe_load((Paths.EVALUATION_GOLD_DIR / "gold_set.yaml").read_text(encoding="utf-8"))
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("id가 중복됨")
    for item in items:
        try:
            if item["answerability"] not in ANSWERABILITY:
                raise ValueError(f"answerability는 {sorted(ANSWERABILITY)} 중 하나")
            if item["question_type"] not in QUESTION_TYPES:
                raise ValueError(f"question_type은 {sorted(QUESTION_TYPES)} 중 하나")
            if (item["answerability"] == "none") != (not item["evidence"]):
                raise ValueError("답할 수 없는(none) 문항만 근거가 비어 있어야 함")
            if (item["answerability"] == "none") != (item["question_type"] == "unanswerable"):
                raise ValueError("answerability none과 question_type unanswerable은 함께 써야 함")
            item["evidence"] = [
                {**resolve(ev, docs), "alt": [resolve(a, docs) for a in ev.get("alt", [])]} for ev in item["evidence"]
            ]
        except ValueError as e:
            raise ValueError(f"{item['id']}: {e}") from None
    return items


def main():
    items = build()
    Paths.EVALUATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(Paths.EVALUATION_OUTPUT_DIR / "gold_set.jsonl", "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    answerability = {a: sum(i["answerability"] == a for i in items) for a in sorted(ANSWERABILITY)}
    types = {t: sum(i["question_type"] == t for i in items) for t in sorted(QUESTION_TYPES)}
    print(f"{len(items)} items {answerability} {types} → {Paths.EVALUATION_OUTPUT_DIR / 'gold_set.jsonl'}")


if __name__ == "__main__":
    main()
