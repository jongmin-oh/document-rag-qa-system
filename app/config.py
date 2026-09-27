from dataclasses import dataclass
from pathlib import Path

import boto3


@dataclass
class Paths:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    APP_INDEX_DIR: Path = BASE_DIR / "app" / "data" / "processed"
    PREPROCESSING_DATA_DIR: Path = BASE_DIR / "preprocessing" / "data"
    PREPROCESSING_RAW_DIR: Path = PREPROCESSING_DATA_DIR / "raw"
    PREPROCESSING_MARKDOWN_DIR: Path = PREPROCESSING_DATA_DIR / "markdown"
    PREPROCESSING_OUTPUT_DIR: Path = PREPROCESSING_DATA_DIR / "processed"
    EVALUATION_DATA_DIR: Path = BASE_DIR / "evaluation" / "data"
    EVALUATION_GOLD_DIR: Path = EVALUATION_DATA_DIR / "gold"
    EVALUATION_OUTPUT_DIR: Path = EVALUATION_DATA_DIR / "processed"
    EVALUATION_REPORTS_DIR: Path = BASE_DIR / "evaluation" / "reports"


SSM_PATH = "/document-rag-qa/"

# API 키는 Parameter Store의 SSM_PATH 아래에 둔다. import 시점에 한 번 읽는다.
_pages = boto3.client("ssm").get_paginator("get_parameters_by_path").paginate(Path=SSM_PATH, WithDecryption=True)
SECRETS = {p["Name"].removeprefix(SSM_PATH): p["Value"] for page in _pages for p in page["Parameters"]}


# 질의 재작성과 답변 생성에 공통으로 넘긴다. 제공사가 결정론을 보장하지는 않는다.
SEED = 42


@dataclass
class GeminiConfig:
    API_KEY: str = SECRETS["GEMINI_API_KEY"]
    LLM_MODEL: str = "gemini-3.7-flash"


@dataclass
class OpenRouterConfig:
    API_KEY: str = SECRETS["OPENROUTER_API_KEY"]
    BASE_URL: str = "https://openrouter.ai/api/v1"
    EMBEDDING_MODEL: str = "perplexity/pplx-embed-v1-4b"
    EMBEDDING_DIM: int = 2560


# 정부 문서와 사용자 질문을 처리하므로 저장·학습하지 않는 제공자만 사용한다.
OPENROUTER_PROVIDER = {
    "require_parameters": True,
    "zdr": True,
    "data_collection": "deny",
}
