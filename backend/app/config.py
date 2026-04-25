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


settings = Settings()
