from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Paths:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    SECRETS_PATH: Path = BASE_DIR.joinpath("app", "secrets.yml")


with open(Paths.SECRETS_PATH, "r", encoding="utf-8") as file:
    SECRETS = yaml.safe_load(file)


@dataclass
class GeminiConfig:
    API_KEY: str = SECRETS["GEMINI"]["API_KEY"]
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIM: int = 3072
    LLM_MODEL: str = "gemini-3.8-flash"


@dataclass
class OpenRouterConfig:
    API_KEY: str = SECRETS.get("OPENROUTER", {}).get("API_KEY", "")
    BASE_URL: str = "https://openrouter.ai/api/v1"
    JUDGE_MODEL: str = "openai/gpt-5.4-mini"
