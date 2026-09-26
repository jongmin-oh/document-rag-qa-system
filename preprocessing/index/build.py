"""청크 → pplx-embed-v1-4b 벡터 인덱스. 제목 경로와 본문을 함께 임베딩한다.

사용법: python -m preprocessing.index.build
입력: app/data/processed/chunks.structure.jsonl
출력: app/data/processed/
  - embeddings.f32    청크 순서대로 이어 붙인 float32 벡터 (L2 정규화)
  - embeddings.json   모델 ID, 차원, 청크 ID 순서
"""

import json
from array import array

from app.config import OpenRouterConfig
from app.index import OUT, body, client, embed, load_chunks


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
