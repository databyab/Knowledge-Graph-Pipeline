from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    gemini_api_key: SecretStr = SecretStr("")
    groq_model: str | None = None
    gemini_model: str | None = None
    neo4j_uri: str = "bolt://127.0.0.1:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("")
    cors_origins: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def load_env_settings() -> EnvSettings:
    return EnvSettings()


def load_yaml(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError("configuration must be a mapping")
    return {str(key): item for key, item in value.items()}
