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
