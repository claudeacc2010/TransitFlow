"""Конфигурация приложения из переменных окружения (раздел 11 спеки)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ — корень бэкенда; .env ищем здесь независимо от cwd.
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # psycopg 3 => схема postgresql+psycopg://
    database_url: str = "postgresql+psycopg://transitflow:transitflow@localhost:5432/transitflow"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    # --- AI-сводка (раздел 4) ---
    # Провайдер: "gemini" | "claude". Без рабочего ключа сводка падает в fallback.
    ai_provider: str = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5-20251001"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
