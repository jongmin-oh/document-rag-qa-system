import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Paths:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    ENV_PATH: Path = BASE_DIR / ".env"


load_dotenv(Paths.ENV_PATH)

# 질의 재작성·답변 생성·Judge 호출에 공통으로 넘긴다. 제공사가 결정론을 보장하지는 않는다.
SEED = 42


@dataclass
class GeminiConfig:
    API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIM: int = 3072
    LLM_MODEL: str = "gemini-3.8-flash"


@dataclass
class OpenRouterConfig:
    API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    BASE_URL: str = "https://openrouter.ai/api/v1"
    JUDGE_MODEL: str = "openai/gpt-6-sol"
