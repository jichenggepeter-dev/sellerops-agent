"""Application settings and filesystem configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "app" / "web"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_prefix="SELLEROPS_",
        extra="ignore",
    )

    env: str = "local"
    db_path: str = "data/sellerops.db"
    cors_origins: str = "*"
    log_level: str = "info"
    triage_provider: str = "mock"
    triage_fallback_to_mock: bool = True
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    slack_webhook_url: str = ""
    github_token: str = ""
    github_repo: str = ""
    stripe_api_key: str = ""
    stripe_allow_live_mode: bool = False

    @property
    def database_path(self) -> Path:
        path = Path(self.db_path)
        if path.is_absolute():
            return path
        return ROOT / path

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
