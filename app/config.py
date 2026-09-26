import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Paths:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    ENV_PATH: Path = BASE_DIR / ".env"


load_dotenv(Paths.ENV_PATH)

# 질의 재작성과 답변 생성에 공통으로 넘긴다. 제공사가 결정론을 보장하지는 않는다.
SEED = 42


@dataclass
class GeminiConfig:
    API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_MODEL: str = "gemini-3.7-flash"


@dataclass
class OpenRouterConfig:
    API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    BASE_URL: str = "https://openrouter.ai/api/v1"
    EMBEDDING_MODEL: str = "perplexity/pplx-embed-v1-4b"
    EMBEDDING_DIM: int = 2560


# 정부 문서와 사용자 질문을 처리하므로 저장·학습하지 않는 제공자만 사용한다.
OPENROUTER_PROVIDER = {
    "require_parameters": True,
    "zdr": True,
    "data_collection": "deny",
}
