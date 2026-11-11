from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Tandem API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/recruitment.db"
    storage_root: Path = Path("./storage")
    max_upload_bytes: int = 10 * 1024 * 1024
    access_token_secret: SecretStr = SecretStr("")
    access_token_ttl_minutes: int = 30
    inference_enabled: bool = False
    inference_provider: str = "auto"
    inference_api_key: SecretStr = SecretStr("")
    inference_chat_model: str = "Qwen/Qwen2.5-72B-Instruct"
    inference_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    inference_reranker_model: str = ""
    inference_timeout_seconds: float = 45
    inference_max_concurrency: int = 2
    worker_poll_seconds: float = 1.5
    worker_lease_seconds: int = 180
    worker_max_attempts: int = 5
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("max_upload_bytes", "access_token_ttl_minutes", "worker_lease_seconds")
    @classmethod
    def positive_integer(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be greater than zero")
        return value

    def validate_auth_secret(self) -> None:
        if len(self.access_token_secret.get_secret_value()) < 32:
            raise ValueError("ACCESS_TOKEN_SECRET must contain at least 32 characters")

    def validate_inference(self) -> None:
        if self.inference_enabled and not all(
            [
                self.inference_api_key.get_secret_value(),
                self.inference_chat_model,
                self.inference_embedding_model,
            ]
        ):
            raise ValueError(
                "Enabled inference requires a hosted API key, chat model, and embedding model"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
