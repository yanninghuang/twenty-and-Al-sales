"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """AI Backend configuration."""

    # Database — defaults to SQLite for zero-setup local dev
    database_url: str = "sqlite+aiosqlite:///./ai_backend.db"
    database_sync_url: str = "sqlite:///./ai_backend.db"

    # LLM
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    default_llm_model: str = "deepseek-chat"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_provider: str = "openai"

    # Twenty CRM connection
    twenty_crm_default_url: str = "http://localhost:3000"
    twenty_crm_graphql_path: str = "/graphql"

    # Scheduler
    risk_evaluation_interval_minutes: int = 240
    profile_refresh_interval_hours: int = 24
    crm_sync_interval_minutes: int = 60

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    api_key_header: str = "X-AI-Backend-API-Key"
    internal_api_key: str = "dev-internal-key-change-in-production"

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
