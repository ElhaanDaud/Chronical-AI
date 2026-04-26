from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.article import Article
from app.models.cluster import Cluster
from app.models.commit import Commit
from app.schemas.story import (
    CatchUpResponse,
    CommitResponse,
    StoryCard,
    StoryDetail,
)
from app.services.summarization import generate_catchup

router = APIRouter()

_stories_cache: dict = {"data": None, "expires_at": datetime.min.replace(tzinfo=timezone.utc)}


def _derive_topic_tokens(topic_label: str) -> list[str]:
    return [t.strip() for t in topic_label.split(" — ") if t.strip()] if topic_label else []


async def _fetch_stories(db: AsyncSession) -> list[StoryCard]:
    article_count_subq = (
        select(func.count())
        .where(Article.cluster_id == Cluster.id)
        .correlate(Cluster)
        .scalar_subquery()
    )

    result = await db.execute(
        select(Cluster, article_count_subq.label("article_count"))
        .where(Cluster.state.in_(["active", "cooling"]))
        .order_by(Cluster.heat_score.desc())
        .options(selectinload(Cluster.commits))
    )
    rows = result.all()

    cards = []
    for cluster, article_count in rows:
        latest_commit = None
        if cluster.commits:
            latest_commit = max(cluster.commits, key=lambda c: c.commit_date)

        cards.append(
            StoryCard(
                id=cluster.id,
                topic_label=cluster.topic_label,
                topic_tokens=_derive_topic_tokens(cluster.topic_label),
                latest_commit_message=latest_commit.message if latest_commit else "",
                heat_score=cluster.heat_score,
                state=cluster.state,
                article_count=article_count,
                last_updated=cluster.updated_at,
            )
        )

    return cards


async def get_cached_stories(db: AsyncSession) -> list[StoryCard]:
    now = datetime.now(timezone.utc)
    if _stories_cache["data"] is not None and now < _stories_cache["expires_at"]:
        return _stories_cache["data"]

    stories = await _fetch_stories(db)
    _stories_cache["data"] = stories
    _stories_cache["expires_at"] = now + timedelta(minutes=5)
    return stories


@router.get("/stories", response_model=list[StoryCard])
@limiter.limit("30/minute")
async def list_stories(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[StoryCard]:
    return await get_cached_stories(db)


def _build_commit_response(commit: Commit, articles_by_id: dict) -> CommitResponse:
    source_articles = [articles_by_id[aid] for aid in (commit.article_ids or []) if aid in articles_by_id]
    return CommitResponse(
        id=commit.id,
        message=commit.message,
        detail=commit.detail,
        commit_date=commit.commit_date,
        source_count=len(source_articles),
        source_urls=[a.url for a in source_articles],
    )


@router.get("/stories/{story_id}", response_model=StoryDetail)
async def get_story(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StoryDetail:
    result = await db.execute(
        select(Cluster)
        .where(Cluster.id == story_id)
        .options(selectinload(Cluster.commits), selectinload(Cluster.articles))
    )
    cluster = result.scalar_one_or_none()

    if not cluster:
        raise HTTPException(status_code=404, detail="Story not found")

    articles_by_id = {a.id: a for a in cluster.articles}
    sorted_commits = sorted(cluster.commits, key=lambda c: c.commit_date, reverse=True)

    return StoryDetail(
        id=cluster.id,
        topic_label=cluster.topic_label,
        topic_tokens=_derive_topic_tokens(cluster.topic_label),
        state=cluster.state,
        heat_score=cluster.heat_score,
        article_count=len(cluster.articles),
        commits=[_build_commit_response(c, articles_by_id) for c in sorted_commits],
        entity_fingerprint=cluster.entity_fingerprint or [],
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
    )


@router.get("/stories/{story_id}/commits", response_model=list[CommitResponse])
async def list_commits(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
) -> list[CommitResponse]:
    cluster = await db.get(Cluster, story_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Story not found")

    result = await db.execute(
        select(Commit)
        .where(Commit.cluster_id == story_id)
        .order_by(Commit.commit_date.desc())
        .limit(limit)
        .offset(offset)
    )
    commits = list(result.scalars().all())

    all_article_ids = set()
    for commit in commits:
        all_article_ids.update(commit.article_ids or [])

    articles_by_id = {}
    if all_article_ids:
        art_result = await db.execute(
            select(Article).where(Article.id.in_(all_article_ids))
        )
        articles_by_id = {a.id: a for a in art_result.scalars().all()}

    return [_build_commit_response(c, articles_by_id) for c in commits]


@router.get("/stories/{story_id}/catchup", response_model=CatchUpResponse)
async def catchup(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CatchUpResponse:
    cluster = await db.get(Cluster, story_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Story not found")

    result = await db.execute(
        select(Commit)
        .where(Commit.cluster_id == story_id)
        .order_by(Commit.commit_date.asc())
    )
    commits = list(result.scalars().all())

    narrative = generate_catchup(commits)

    time_span_days = 0
    if len(commits) >= 2:
        delta = commits[-1].commit_date - commits[0].commit_date
        time_span_days = max(delta.days, 1)
    elif commits:
        time_span_days = 1

    return CatchUpResponse(
        story_id=story_id,
        narrative=narrative,
        commit_count=len(commits),
        time_span_days=time_span_days,
    )
