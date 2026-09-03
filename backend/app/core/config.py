"""
Application configuration.

All runtime configuration comes from environment variables (loaded from a
.env file in local development). Nothing here should be a hard-coded secret.
See backend/.env.example for the full list of variables this app understands.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # General
    environment: str = "development"
    app_name: str = "AI Interviewer API"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "ai_interviewer"

    # LLM provider (Anthropic Claude). Left blank by default so the app can
    # still boot (health check, dashboard) before any AI features are wired up.
    # Default model is Claude Opus 5 (Anthropic's current recommended default
    # for general use); override via ANTHROPIC_MODEL if you want a cheaper
    # model (e.g. "claude-sonnet-5") for higher-volume practice sessions.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"

    # Auth (wired up in a later milestone; placeholder now so the shape exists)
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # CORS - the Next.js dev server
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - env is only read once per process."""
    return Settings()


settings = get_settings()
