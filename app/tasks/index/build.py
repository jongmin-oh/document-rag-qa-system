"""청크 → Gemini Embedding 2 벡터 인덱스. 실험 조건(decision/chunking_strategy.md 4절)마다 따로 만든다.

사용법: python -m app.tasks.index.build [A B C]   (조건을 생략하면 전부)
입력: app/data/processed/chunks.{fixed,structure}.jsonl
출력: app/data/processed/
  - embeddings.{조건}.f32    청크 순서대로 이어 붙인 float32 벡터 (L2 정규화)
  - embeddings.{조건}.json   모델 ID, 차원, 청크 ID 순서
"""

import json
import math
import sys
from array import array

from google import genai

from app.config import GeminiConfig
from app.tasks.ingest.build import OUT

CONDITIONS = {  # 조건 → (청크 파일, 제목 경로 접두어를 임베딩에 넣는가)
    "A": ("chunks.fixed.jsonl", False),
    "B": ("chunks.structure.jsonl", False),
    "C": ("chunks.structure.jsonl", True),
}


def load_chunks(condition: str) -> list[dict]:
    with open(OUT / CONDITIONS[condition][0], encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def body(chunk: dict) -> str:
    """나뉜 Q&A 조각은 원래 질문을 앞에 다시 붙인다."""
    return f"{chunk['question_prefix']}\n{chunk['text']}" if chunk["question_prefix"] else chunk["text"]


def document_text(chunk: dict, condition: str) -> str:
    # decision/models.md: Gemini Embedding 2는 task_type 대신 접두어로 문서를 표시한다. 제목이 없으면 "none".
    title = chunk["title_prefix"] if CONDITIONS[condition][1] else "none"
    return f"title: {title} | text: {body(chunk)}"


def client() -> genai.Client:
    # 무료 등급은 분당 요청 한도가 낮아 429를 받으면 지수 백오프로 재시도한다.
    retry = {"attempts": 10, "initial_delay": 5, "max_delay": 60}
    return genai.Client(api_key=GeminiConfig.API_KEY, http_options={"retry_options": retry})


def embed(client: genai.Client, text: str) -> list[float]:
    # 여러 텍스트를 한 요청에 넣으면 하나의 벡터로 합쳐지므로 텍스트마다 호출한다.
    values = client.models.embed_content(
        model=GeminiConfig.EMBEDDING_MODEL,
        contents=text,
        config={"output_dimensionality": GeminiConfig.EMBEDDING_DIM},
    ).embeddings[0].values
    norm = math.sqrt(sum(v * v for v in values))
    return [v / norm for v in values]


def load_meta(condition: str) -> dict:
    return json.loads((OUT / f"embeddings.{condition}.json").read_text(encoding="utf-8"))


def load_index(condition: str) -> tuple[list[str], list[list[float]]]:
    meta = load_meta(condition)
    flat = array("f")
    flat.frombytes((OUT / f"embeddings.{condition}.f32").read_bytes())
    dim = meta["dim"]
    return meta["chunk_ids"], [flat[i : i + dim] for i in range(0, len(flat), dim)]


def build(gemini: genai.Client, condition: str):
    chunks = load_chunks(condition)
    flat = array("f")
    for i, c in enumerate(chunks, 1):
        flat.extend(embed(gemini, document_text(c, condition)))
        print(f"\r{condition}: {i}/{len(chunks)}", end="", flush=True)
    (OUT / f"embeddings.{condition}.f32").write_bytes(flat.tobytes())
    meta = {
        "model": GeminiConfig.EMBEDDING_MODEL,
        "dim": GeminiConfig.EMBEDDING_DIM,
        "chunk_ids": [c["chunk_id"] for c in chunks],
    }
    (OUT / f"embeddings.{condition}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{condition}: {len(chunks)} vectors ({meta['dim']}d) → {OUT}")


def main():
    gemini = client()
    for condition in sys.argv[1:] or CONDITIONS:
        build(gemini, condition)


if __name__ == "__main__":
    main()
