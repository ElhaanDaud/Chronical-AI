import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from app.core.logging import logger
from app.models.cluster import Cluster
from app.models.commit import Commit
from app.services.clustering import clean_text

GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
BACKFILL_DAYS = 20
DAYS_PER_WINDOW = 5
MAX_ARTICLES_PER_WINDOW = 25


def _build_gdelt_url(query: str, start_date: datetime, end_date: datetime) -> str:
    start_str = start_date.strftime("%Y%m%d%H%M%S")
    end_str = end_date.strftime("%Y%m%d%H%M%S")
    return (
        f"{GDELT_API_URL}?query={query} sourcelang:english"
        f"&startdatetime={start_str}&enddatetime={end_str}"
        f"&mode=artlist&maxrecords={MAX_ARTICLES_PER_WINDOW}"
        f"&format=json"
    )


async def _fetch_gdelt_window(
    client: httpx.AsyncClient,
    query: str,
    start: datetime,
    end: datetime,
) -> list[dict]:
    url = _build_gdelt_url(query, start, end)
    try:
        resp = await client.get(url, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("articles", [])
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("GDELT rate limited, waiting 10s")
            await asyncio.sleep(10)
        else:
            logger.warning(f"GDELT HTTP error: {e.response.status_code}")
        return []
    except Exception as e:
        logger.warning(f"GDELT fetch failed: {e}")
        return []


def _extract_keywords(topic_label: str) -> str:
    tokens = topic_label.replace(" — ", " ").replace("—", " ").split()
    stop = {"the", "a", "an", "and", "or", "in", "on", "of", "for", "to", "is", "are", "was", "were", "has", "have", "with", "from", "at", "by"}
    keywords = [t for t in tokens if t.lower() not in stop and len(t) > 2]
    if len(keywords) < 2:
        keywords = tokens[:3]
    return " ".join(keywords[:4])


async def _summarize_gdelt_articles(
    topic_label: str,
    articles: list[dict],
    window_start: datetime,
) -> tuple[str, str]:
    from app.services.llm import generate_commit_summary

    titles = [a.get("title", "") for a in articles[:8]]
    summaries = [clean_text(a.get("seendate", "")) for a in articles[:8]]

    result = await generate_commit_summary(topic_label, titles, summaries)
    if result:
        return result

    if titles:
        message = titles[0][:150]
        detail = ". ".join(t for t in titles[:3] if t)
        return message, detail

    date_str = window_start.strftime("%B %d")
    return f"Developments on {date_str}", f"Coverage continued around {topic_label}."


async def backfill_cluster_history(
    cluster: Cluster,
    db_session,
) -> int:
    query = _extract_keywords(cluster.topic_label)
    if not query.strip():
        return 0

    now = datetime.now(timezone.utc)
    existing_dates = set()
    for commit in (cluster.commits or []):
        existing_dates.add(commit.commit_date.date())

    windows = []
    for i in range(0, BACKFILL_DAYS, DAYS_PER_WINDOW):
        window_end = now - timedelta(days=i)
        window_start = now - timedelta(days=i + DAYS_PER_WINDOW)
        if window_start.date() not in existing_dates:
            windows.append((window_start, window_end))

    if not windows:
        return 0

    windows.reverse()

    commits_created = 0
    async with httpx.AsyncClient() as client:
        for window_start, window_end in windows:
            await asyncio.sleep(1)

            articles = await _fetch_gdelt_window(client, query, window_start, window_end)
            if not articles:
                continue

            message, detail = await _summarize_gdelt_articles(
                cluster.topic_label, articles, window_start,
            )

            commit = Commit(
                id=uuid.uuid4(),
                cluster_id=cluster.id,
                message=message,
                detail=detail,
                article_ids=[],
                commit_date=window_start + timedelta(days=DAYS_PER_WINDOW // 2),
            )
            db_session.add(commit)
            commits_created += 1

    return commits_created


async def run_gdelt_backfill(db_session) -> int:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db_session.execute(
        select(Cluster)
        .where(Cluster.state.in_(["active", "cooling"]))
        .options(selectinload(Cluster.commits))
    )
    clusters = list(result.scalars().all())

    if not clusters:
        logger.info("No clusters for GDELT backfill")
        return 0

    total_commits = 0
    for cluster in clusters:
        if len(cluster.commits or []) >= 4:
            continue

        created = await backfill_cluster_history(cluster, db_session)
        total_commits += created
        logger.info(f"GDELT backfill: {created} commits for '{cluster.topic_label}'")

    await db_session.commit()
    logger.info(f"GDELT backfill complete: {total_commits} total commits created")
    return total_commits
