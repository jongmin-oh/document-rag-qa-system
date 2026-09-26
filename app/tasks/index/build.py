"""청크 → pplx-embed-v1-4b 벡터 인덱스. 제목 경로와 본문을 함께 임베딩한다.

사용법: python -m app.tasks.index.build
입력: app/data/processed/chunks.structure.jsonl
출력: app/data/processed/
  - embeddings.f32    청크 순서대로 이어 붙인 float32 벡터 (L2 정규화)
  - embeddings.json   모델 ID, 차원, 청크 ID 순서
"""

import json
import math
from array import array

from openai import OpenAI

from app.config import OPENROUTER_PROVIDER, OpenRouterConfig
from app.tasks.ingest.build import OUT


def load_chunks() -> list[dict]:
    with open(OUT / "chunks.structure.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def body(chunk: dict) -> str:
    """나뉜 Q&A 조각은 원래 질문을 앞에 다시 붙인다."""
    return f"{chunk['question_prefix']}\n{chunk['text']}" if chunk["question_prefix"] else chunk["text"]


def client() -> OpenAI:
    if not OpenRouterConfig.API_KEY:
        raise ValueError(".env에 OPENROUTER_API_KEY를 설정하세요")
    return OpenAI(
        api_key=OpenRouterConfig.API_KEY,
        base_url=OpenRouterConfig.BASE_URL,
        max_retries=10,
        default_headers={"X-OpenRouter-Title": "document-rag-qa-system"},
    )


def embed(client: OpenAI, text: str) -> list[float]:
    values = client.embeddings.create(
        model=OpenRouterConfig.EMBEDDING_MODEL,
        input=text,
        encoding_format="float",
        extra_body={"provider": OPENROUTER_PROVIDER},
    ).data[0].embedding
    if len(values) != OpenRouterConfig.EMBEDDING_DIM:
        raise ValueError(f"임베딩 차원이 {len(values)}입니다. 예상값: {OpenRouterConfig.EMBEDDING_DIM}")
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        raise ValueError("임베딩 모델이 영벡터를 반환했습니다")
    return [v / norm for v in values]


def load_meta() -> dict:
    return json.loads((OUT / "embeddings.json").read_text(encoding="utf-8"))


def load_index() -> tuple[list[str], list[list[float]]]:
    meta = load_meta()
    expected = (OpenRouterConfig.EMBEDDING_MODEL, OpenRouterConfig.EMBEDDING_DIM)
    actual = (meta["model"], meta["dim"])
    if actual != expected:
        raise ValueError(
            f"인덱스가 현재 임베딩 설정과 다릅니다({actual[0]}, {actual[1]}차원). "
            "python -m app.tasks.index.build 로 다시 생성하세요."
        )
    flat = array("f")
    flat.frombytes((OUT / "embeddings.f32").read_bytes())
    dim = meta["dim"]
    return meta["chunk_ids"], [flat[i : i + dim] for i in range(0, len(flat), dim)]


def main():
    openrouter = client()
    chunks = load_chunks()
    flat = array("f")
    for i, c in enumerate(chunks, 1):
        flat.extend(embed(openrouter, f"{c['title_prefix']}\n{body(c)}"))
        print(f"\r{i}/{len(chunks)}", end="", flush=True)
    (OUT / "embeddings.f32").write_bytes(flat.tobytes())
    meta = {
        "model": OpenRouterConfig.EMBEDDING_MODEL,
        "dim": OpenRouterConfig.EMBEDDING_DIM,
        "chunk_ids": [c["chunk_id"] for c in chunks],
    }
    (OUT / "embeddings.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(chunks)} vectors ({meta['dim']}d) → {OUT}")


if __name__ == "__main__":
    main()
