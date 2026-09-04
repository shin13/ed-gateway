from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_ENV: str = "development"
    APP_NAME: str = "ED Gateway"
    LOG_LEVEL: str = "INFO"
    DEMO_MODE: bool = True

    LLM_PROVIDER: Literal["mock", "openai_compatible"] = "mock"
    LLM_MODEL: str = ""
    LLM_BASE_URL: str = ""
    LLM_API_KEY: SecretStr = Field(default=SecretStr(""), repr=False)
    LLM_TIMEOUT_SECONDS: float = Field(default=30, gt=0)
    LLM_MAX_RETRIES: int = Field(default=1, ge=0, le=5)
    LLM_TEMPERATURE: float = Field(default=0, ge=0, le=2)

    POSTGRES_DB: str = "ed_gateway"
    POSTGRES_USER: str = "ed_gateway"
    POSTGRES_PASSWORD: SecretStr = Field(default=SecretStr(""), repr=False)
    DATABASE_URL: SecretStr = Field(
        default=SecretStr("postgresql+asyncpg://ed_gateway:ed_gateway@db:5432/ed_gateway"),
        repr=False,
    )

    API_HOST: str = "0.0.0.0"
    API_PORT: int = Field(default=8001, ge=1, le=65535)
    API_BASE_URL: str = "http://api:8001"
    CHAINLIT_HOST: str = "0.0.0.0"
    CHAINLIT_PORT: int = Field(default=8000, ge=1, le=65535)

    @model_validator(mode="after")
    def validate_provider(self) -> "Settings":
        if self.LLM_PROVIDER == "openai_compatible":
            missing = [
                name
                for name, value in (
                    ("LLM_MODEL", self.LLM_MODEL),
                    ("LLM_BASE_URL", self.LLM_BASE_URL),
                    ("LLM_API_KEY", self.LLM_API_KEY.get_secret_value()),
                )
                if not value
            ]
            if missing:
                raise ValueError("openai_compatible provider requires: " + ", ".join(missing))
        return self

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
