from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    last_ingestion: datetime | None
    active_stories: int
    total_articles: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
