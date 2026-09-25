"""검색 평가: Gold Set 질문으로 검색해 근거를 얼마나 회수하는지 잰다.

사용법: python -m app.tasks.eval.retrieval
입력: app/data/processed/gold_set.jsonl, 현재 인덱스(app/data/processed/embeddings.*)
출력: reports/retrieval.md (요약 리포트), reports/retrieval.json (문항별 결과)

지표 정의는 decision/chunking_strategy.md 4절을 따른다.
- 근거 회수: top-k 청크가 근거 구간을 THRESHOLD 이상 덮으면 회수. alt가 있으면 가장 많이 덮인 쪽을 쓴다.
- 답할 수 없는(none) 문항은 근거가 없어 검색 평가에서 뺀다.
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.tasks.index.build import client
from app.tasks.ingest.build import OUT
from app.tasks.qa.ask import search

REPORTS = Path(__file__).resolve().parents[3] / "reports"
KS = (1, 3, 5, 10)
MAIN_K = 5  # 답변 생성에 넘기는 청크 수(ask.TOP_K)와 같다
THRESHOLD = 0.8
THRESHOLDS = (0.5, 0.8, 1.0)  # 임계값에 따라 결론이 바뀌는지 확인
METRICS = ("hit", "recall", "coverage", "precision")


def length(span: dict) -> int:
    return span["char_end"] - span["char_start"]


def overlap(span: dict, chunk: dict) -> int:
    if span["doc_id"] != chunk["doc_id"]:
        return 0
    return max(0, min(span["char_end"], chunk["char_end"]) - max(span["char_start"], chunk["char_start"]))


def coverage(span: dict, chunks: list[dict]) -> float:
    # ponytail: 같은 조건의 청크끼리는 겹치지 않으므로(overlap 0%) 겹친 길이의 합이 곧 합집합 길이다.
    return sum(overlap(span, c) for c in chunks) / length(span)


def score(evidence: list[dict], chunks: list[dict], threshold: float = THRESHOLD) -> dict:
    """한 문항의 top-k 청크(chunks)에 대한 지표."""
    picked = [max(((s, coverage(s, chunks)) for s in [ev, *ev["alt"]]), key=lambda x: x[1]) for ev in evidence]
    recovered = [cov >= threshold for _, cov in picked]
    spans = [s for ev in evidence for s in [ev, *ev["alt"]]]
    return {
        "hit": float(any(recovered)),
        "recall": sum(recovered) / len(evidence),
        "coverage": sum(cov * length(s) for s, cov in picked) / sum(length(s) for s, _ in picked),
        "precision": sum(any(overlap(s, c) for s in spans) for c in chunks) / len(chunks),
    }


def mean(rows: list[dict], k: int, metric: str) -> float:
    return sum(r["scores"][str(k)][metric] for r in rows) / len(rows)


def git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()


def evaluate() -> dict:
    gemini = client()
    items = [json.loads(line) for line in open(OUT / "gold_set.jsonl", encoding="utf-8")]
    items = [i for i in items if i["evidence"]]
    rows = []
    for n, item in enumerate(items, 1):
        ranked = [c for _, c in search(gemini, item["question"], k=max(KS))]
        rows.append(
            {
                "id": item["id"],
                "question_type": item["question_type"],
                "answerability": item["answerability"],
                "top": [c["chunk_id"] for c in ranked],
                "scores": {str(k): score(item["evidence"], ranked[:k]) for k in KS},
                "recall_by_threshold": {str(t): score(item["evidence"], ranked[:MAIN_K], t)["recall"] for t in THRESHOLDS},
            }
        )
        print(f"\r{n}/{len(items)}", end="", flush=True)
    print()
    index = json.loads((OUT / "embeddings.json").read_text(encoding="utf-8"))
    return {
        "meta": {
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_commit": git_commit(),
            "embedding_model": index["model"],
            "embedding_dim": index["dim"],
            "n_chunks": len(index["chunk_ids"]),
            "n_items": len(rows),
            "threshold": THRESHOLD,
        },
        "items": rows,
    }


def report(result: dict) -> str:
    rows, meta = result["items"], result["meta"]
    lines = [
        "# 검색 평가 리포트",
        "",
        f"- 실행: {meta['run_at']} / 커밋 `{meta['git_commit']}`",
        f"- 인덱스: `{meta['embedding_model']}` {meta['embedding_dim']}차원, 청크 {meta['n_chunks']}개",
        f"- 문항: {meta['n_items']}개 (answerability none 제외), 근거 회수 임계값 {meta['threshold']}",
        "- 지표 정의: `decision/chunking_strategy.md` 4절",
        "",
        "## 전체",
        "",
        "| k | Hit | Recall | Coverage | Precision |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {k} | " + " | ".join(f"{mean(rows, k, m):.3f}" for m in METRICS) + " |" for k in KS]
    lines += ["", f"## 임계값별 Recall@{MAIN_K}", "", "| 임계값 | Recall |", "|---|---|"]
    lines += [f"| {t} | {sum(r['recall_by_threshold'][str(t)] for r in rows) / len(rows):.3f} |" for t in THRESHOLDS]
    lines += ["", f"## 그룹별 @{MAIN_K}", "", "| 그룹 | 문항 | Hit | Recall | Coverage | Precision |", "|---|---|---|---|---|---|"]
    for field in ("question_type", "answerability"):
        for value in sorted({r[field] for r in rows}):
            group = [r for r in rows if r[field] == value]
            lines.append(
                f"| {value} | {len(group)} | " + " | ".join(f"{mean(group, MAIN_K, m):.3f}" for m in METRICS) + " |"
            )
    lines += ["", f"## 문항별 @{MAIN_K}", "", f"| id | 유형 | Hit | Recall | Coverage | top-{MAIN_K} |", "|---|---|---|---|---|---|"]
    for r in rows:
        s = r["scores"][str(MAIN_K)]
        top = ", ".join(r["top"][:MAIN_K])
        lines.append(f"| {r['id']} | {r['question_type']} | {s['hit']:.0f} | {s['recall']:.2f} | {s['coverage']:.2f} | {top} |")
    return "\n".join(lines) + "\n"


def main():
    result = evaluate()
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "retrieval.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    (REPORTS / "retrieval.md").write_text(report(result), encoding="utf-8")
    print(f"→ {REPORTS / 'retrieval.md'}")


if __name__ == "__main__":
    main()
