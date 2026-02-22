"""
Application configuration using Pydantic Settings.
All values are loaded from environment variables (or .env file).
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Central configuration sourced from environment variables."""

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "CodeQuery API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://codequery:codequery@db:5432/codequery"
    DATABASE_URL_SYNC: str = "postgresql://codequery:codequery@db:5432/codequery"

    # ── Redis / Celery ───────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── AI / Embeddings ──────────────────────────────────
    # We default to a free, local model via HuggingFace sentence-transformers.
    # Switch to OpenAI by setting OPENAI_API_KEY.
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # free HuggingFace model
    EMBEDDING_DIMENSION: int = 384  # dimension for all-MiniLM-L6-v2
    LLM_MODEL: str = "mistral"  # Ollama model name (free, local)

    # ── Ollama (free local LLM) ──────────────────────────
    OLLAMA_BASE_URL: str = "http://ollama:11434"

    # ── Git clone directory ──────────────────────────────
    CLONE_DIR: str = "/tmp/codequery_repos"

    # ── Security ─────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    API_KEY: str = ""  # optional API key auth

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
