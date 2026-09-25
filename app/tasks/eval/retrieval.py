"""검색 평가: Gold Set 질문으로 모든 검색 조건을 돌려 근거를 얼마나 회수하는지 비교한다.

사용법: python -m app.tasks.eval.retrieval
입력: app/data/processed/gold_set.jsonl, 조건별 인덱스(app/data/processed/embeddings.{A,B,C}.*)
출력: reports/retrieval.md (요약 리포트), reports/retrieval.json (조건·문항별 결과)

지표와 가설은 decision/chunking_strategy.md 4절을 따른다.
- 근거 회수: top-k 청크가 근거 구간을 THRESHOLD 이상 덮으면 회수. alt가 있으면 가장 많이 덮인 쪽을 쓴다.
- 답할 수 없는(none) 문항은 근거가 없어 검색 평가에서 뺀다.
- 질문 임베딩은 조건과 무관하므로 문항마다 한 번만 만든다.
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.tasks.index.build import client, load_meta
from app.tasks.ingest.build import OUT
from app.tasks.qa.search import BM25_B, BM25_K1, RETRIEVERS, RRF_K, embed_query, rank

REPORTS = Path(__file__).resolve().parents[3] / "reports"
KS = (1, 3, 5, 10)
MAIN_K = 5  # 답변 생성에 넘기는 청크 수(ask.TOP_K)와 같다
THRESHOLD = 0.8
THRESHOLDS = (0.5, 0.8, 1.0)  # 임계값에 따라 결론이 바뀌는지 확인
METRICS = ("hit", "recall", "coverage", "precision")
COMPARISONS = [("A", "B", "H1 경계 방식"), ("B", "C", "H2 제목 접두어"), ("C", "C_hybrid", "H3 BM25 결합")]


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


def other_doc_rate(evidence: list[dict], chunks: list[dict]) -> float | None:
    """근거가 한 문서에만 있는 문항에서 top-k 중 다른 문서 청크의 비율 (H2). 근거가 두 문서에 걸치면 None."""
    docs = {s["doc_id"] for ev in evidence for s in [ev, *ev["alt"]]}
    if len(docs) != 1:
        return None
    return sum(c["doc_id"] not in docs for c in chunks) / len(chunks)


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()


def evaluate() -> dict:
    gemini = client()
    items = [json.loads(line) for line in open(OUT / "gold_set.jsonl", encoding="utf-8")]
    items = [i for i in items if i["evidence"]]
    rows = {r: [] for r in RETRIEVERS}
    for n, item in enumerate(items, 1):
        query_vec = embed_query(gemini, item["question"])
        for r in RETRIEVERS:
            ranked = [c for _, c in rank(query_vec, item["question"], r, max(KS))]
            rows[r].append(
                {
                    "id": item["id"],
                    "question_type": item["question_type"],
                    "top": [c["chunk_id"] for c in ranked],
                    "scores": {str(k): score(item["evidence"], ranked[:k]) for k in KS},
                    "recall_by_threshold": {
                        str(t): score(item["evidence"], ranked[:MAIN_K], t)["recall"] for t in THRESHOLDS
                    },
                    "other_doc_rate": other_doc_rate(item["evidence"], ranked[:MAIN_K]),
                }
            )
        print(f"\r{n}/{len(items)}", end="", flush=True)
    print()
    meta = load_meta("C")
    return {
        "meta": {
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_commit": git_commit(),
            "embedding_model": meta["model"],
            "embedding_dim": meta["dim"],
            "n_chunks": {c: len(load_meta(c)["chunk_ids"]) for c in ("A", "B", "C")},
            "bm25": {"k1": BM25_K1, "b": BM25_B, "tokens": "char 2-gram"},
            "rrf_k": RRF_K,
            "n_items": len(items),
            "threshold": THRESHOLD,
        },
        "retrievers": rows,
    }


def metric(rows: list[dict], name: str, k: int = MAIN_K) -> float:
    return mean([r["scores"][str(k)][name] for r in rows])


def table(header: list[str], body: list[list]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(map(str, r)) + " |" for r in body]


def report(result: dict) -> str:
    meta, runs = result["meta"], result["retrievers"]
    names = list(runs)
    ids = [r["id"] for r in runs[names[0]]]
    recall = {n: {r["id"]: r["scores"][str(MAIN_K)]["recall"] for r in runs[n]} for n in names}
    lines = [
        "# 검색 평가 리포트",
        "",
        f"- 실행: {meta['run_at']} / 커밋 `{meta['git_commit']}`",
        f"- 임베딩: `{meta['embedding_model']}` {meta['embedding_dim']}차원 / 청크 수: "
        + ", ".join(f"{c} {n}개" for c, n in meta["n_chunks"].items()),
        f"- BM25: 글자 2-gram, k1={meta['bm25']['k1']}, b={meta['bm25']['b']} / RRF k={meta['rrf_k']}",
        f"- 문항: {meta['n_items']}개 (answerability none 제외), 근거 회수 임계값 {meta['threshold']}",
        "- 조건과 지표 정의: `decision/chunking_strategy.md` 4절",
        "",
        f"## 조건별 요약 (@{MAIN_K})",
        "",
    ]
    lines += table(
        ["조건", "Hit", "Recall", "Coverage", "Precision", "Recall@10", "다른 문서 비율"],
        [
            [n]
            + [f"{metric(runs[n], m):.3f}" for m in METRICS]
            + [f"{metric(runs[n], 'recall', 10):.3f}"]
            + [f"{mean([r['other_doc_rate'] for r in runs[n] if r['other_doc_rate'] is not None]):.3f}"]
            for n in names
        ],
    )
    lines += ["", f"## 가설별 비교 (문항 단위 Recall@{MAIN_K})", ""]
    lines += table(
        ["비교", "가설", "ΔRecall", "좋아짐", "나빠짐", "같음"],
        [
            [
                f"{a} → {b}",
                h,
                f"{mean([recall[b][i] - recall[a][i] for i in ids]):+.3f}",
                sum(recall[b][i] > recall[a][i] for i in ids),
                sum(recall[b][i] < recall[a][i] for i in ids),
                sum(recall[b][i] == recall[a][i] for i in ids),
            ]
            for a, b, h in COMPARISONS
        ],
    )
    types = sorted({r["question_type"] for r in runs[names[0]]})
    lines += ["", f"## 질문 유형별 Recall@{MAIN_K}", ""]
    lines += table(
        ["유형", "문항"] + names,
        [
            [t, sum(r["question_type"] == t for r in runs[names[0]])]
            + [f"{metric([r for r in runs[n] if r['question_type'] == t], 'recall'):.3f}" for n in names]
            for t in types
        ],
    )
    lines += ["", "## k별 Recall", ""]
    lines += table(["k"] + names, [[k] + [f"{metric(runs[n], 'recall', k):.3f}" for n in names] for k in KS])
    lines += ["", f"## 임계값별 Recall@{MAIN_K}", ""]
    lines += table(
        ["임계값"] + names,
        [[t] + [f"{mean([r['recall_by_threshold'][str(t)] for r in runs[n]]):.3f}" for n in names] for t in THRESHOLDS],
    )
    lines += ["", f"## 문항별 Recall@{MAIN_K}", ""]
    lines += table(
        ["id", "유형"] + names,
        [[i, r["question_type"]] + [f"{recall[n][i]:.2f}" for n in names] for i, r in zip(ids, runs[names[0]])],
    )
    return "\n".join(lines) + "\n"


def main():
    result = evaluate()
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "retrieval.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    (REPORTS / "retrieval.md").write_text(report(result), encoding="utf-8")
    print(f"→ {REPORTS / 'retrieval.md'}")


if __name__ == "__main__":
    main()
