"""OpenRouter 임베딩 인덱스 테스트."""

import json
import math
from types import SimpleNamespace

import pytest

from app.config import OPENROUTER_PROVIDER, OpenRouterConfig
from app.tasks.index import build


def test_embed_uses_pplx_and_normalizes_vector():
    class Embeddings:
        kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            vector = [3.0, 4.0] + [0.0] * (OpenRouterConfig.EMBEDDING_DIM - 2)
            return SimpleNamespace(data=[SimpleNamespace(embedding=vector)])

    embeddings = Embeddings()
    client = SimpleNamespace(embeddings=embeddings)
    vector = build.embed(client, "검색할 문장")

    assert math.isclose(sum(v * v for v in vector), 1.0)
    assert vector[:2] == [0.6, 0.8]
    assert embeddings.kwargs["model"] == OpenRouterConfig.EMBEDDING_MODEL
    assert embeddings.kwargs["input"] == "검색할 문장"
    assert embeddings.kwargs["extra_body"]["provider"] == OPENROUTER_PROVIDER


def test_load_index_rejects_stale_embedding_model(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path)
    (tmp_path / "embeddings.json").write_text(
        json.dumps({"model": "old-model", "dim": 3, "chunk_ids": []}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="다시 생성하세요"):
        build.load_index()
