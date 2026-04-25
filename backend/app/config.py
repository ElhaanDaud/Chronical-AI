from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = (
        "postgresql+asyncpg://chronicle:chronicle_dev@localhost:5432/chronicle"
    )
    frontend_url: str = "http://localhost:3000"
    ingestion_interval_minutes: int = 30
    clustering_interval_hours: int = 2
    article_retention_days: int = 30

    groq_api_key: str = ""
    llm_provider: str = "groq"
    llm_model: str = "ai/llama3.2:1B-Q4_0"
    llm_base_url: str = "http://model-runner.docker.internal/engines/v1"
    embedding_model: str = "ai/qwen3-embedding:0.6B-F16"
    embedding_base_url: str = "http://model-runner.docker.internal/engines/llama.cpp/v1"


settings = Settings()
