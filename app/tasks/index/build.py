"""청크 → Gemini Embedding 2 벡터 인덱스. 임베딩 입력에 제목 경로 접두어를 넣는다.

사용법: python -m app.tasks.index.build
입력: app/data/processed/chunks.structure.jsonl
출력: app/data/processed/
  - embeddings.f32    청크 순서대로 이어 붙인 float32 벡터 (L2 정규화)
  - embeddings.json   모델 ID, 차원, 청크 ID 순서
"""

import json
import math
from array import array

from google import genai

from app.config import GeminiConfig
from app.tasks.ingest.build import OUT


def load_chunks() -> list[dict]:
    with open(OUT / "chunks.structure.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def body(chunk: dict) -> str:
    """나뉜 Q&A 조각은 원래 질문을 앞에 다시 붙인다."""
    return f"{chunk['question_prefix']}\n{chunk['text']}" if chunk["question_prefix"] else chunk["text"]


def client() -> genai.Client:
    if not GeminiConfig.API_KEY:
        raise ValueError(".env에 GEMINI_API_KEY를 설정하세요")
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


def load_meta() -> dict:
    return json.loads((OUT / "embeddings.json").read_text(encoding="utf-8"))


def load_index() -> tuple[list[str], list[list[float]]]:
    meta = load_meta()
    flat = array("f")
    flat.frombytes((OUT / "embeddings.f32").read_bytes())
    dim = meta["dim"]
    return meta["chunk_ids"], [flat[i : i + dim] for i in range(0, len(flat), dim)]


def main():
    gemini = client()
    chunks = load_chunks()
    flat = array("f")
    for i, c in enumerate(chunks, 1):
        # decision/models.md: Gemini Embedding 2는 task_type 대신 접두어로 문서를 표시한다.
        flat.extend(embed(gemini, f"title: {c['title_prefix']} | text: {body(c)}"))
        print(f"\r{i}/{len(chunks)}", end="", flush=True)
    (OUT / "embeddings.f32").write_bytes(flat.tobytes())
    meta = {
        "model": GeminiConfig.EMBEDDING_MODEL,
        "dim": GeminiConfig.EMBEDDING_DIM,
        "chunk_ids": [c["chunk_id"] for c in chunks],
    }
    (OUT / "embeddings.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(chunks)} vectors ({meta['dim']}d) → {OUT}")


if __name__ == "__main__":
    main()
