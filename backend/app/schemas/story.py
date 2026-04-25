from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StoryCard(BaseModel):
    id: UUID
    topic_label: str
    topic_tokens: list[str]
    latest_commit_message: str
    heat_score: float
    state: str
    article_count: int
    last_updated: datetime

    model_config = {"from_attributes": True}


class StoryDetail(BaseModel):
    id: UUID
    topic_label: str
    topic_tokens: list[str]
    state: str
    heat_score: float
    article_count: int
    commits: list["CommitResponse"]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommitResponse(BaseModel):
    id: UUID
    message: str
    detail: str
    commit_date: datetime
    source_count: int
    source_urls: list[str]

    model_config = {"from_attributes": True}


class CatchUpResponse(BaseModel):
    story_id: UUID
    narrative: str
    commit_count: int
    time_span_days: int


class SearchResult(BaseModel):
    id: UUID
    title: str
    summary: str | None
    source: str
    published_at: datetime
    cluster_id: UUID | None

    model_config = {"from_attributes": True}
