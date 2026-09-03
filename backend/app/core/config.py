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

    # Which LLMClient app/ai/factory.py should build (see LLMClient in
    # app/ai/base.py for the full interface):
    #   "auto"       - (default) Anthropic if ANTHROPIC_API_KEY is set,
    #                  otherwise the deterministic stub. Preserves the
    #                  original zero-config behavior.
    #   "stub"       - force the deterministic stub regardless of any keys.
    #   "anthropic"  - force Anthropic; errors at startup if
    #                  ANTHROPIC_API_KEY is unset (loud, not a silent
    #                  fallback to the stub).
    #   "openrouter" - force OpenRouter; errors at startup if
    #                  OPENROUTER_API_KEY is unset.
    llm_provider: str = "auto"

    # --- Anthropic Claude (direct) ------------------------------------
    # Left blank by default so the app can still boot (health check,
    # dashboard) before any AI features are wired up. Default model is
    # Claude Opus 5 (Anthropic's current recommended default for general
    # use); override via ANTHROPIC_MODEL if you want a cheaper model (e.g.
    # "claude-sonnet-5") for higher-volume practice sessions.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"

    # --- OpenRouter (https://openrouter.ai) -----------------------------
    # An OpenAI-API-compatible proxy in front of many model providers -
    # OpenRouterLLMClient uses the `openai` SDK pointed at this base_url,
    # OpenRouter's own documented integration approach.
    openrouter_api_key: str = ""
    # anthropic/claude-sonnet-5 is a solid default; OpenRouter is commonly
    # used specifically to reach non-Anthropic models too, so this is
    # freely overridable via OPENROUTER_MODEL - never hardcoded elsewhere
    # in the codebase.
    openrouter_model: str = "anthropic/claude-sonnet-5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 60.0

    # Auth (wired up in a later milestone; placeholder now so the shape exists)
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # CORS - the Next.js dev server
    cors_origins: list[str] = ["http://localhost:3000"]

    # Resume uploads (Milestone 4)
    max_resume_size_bytes: int = 5 * 1024 * 1024  # 5MB

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
