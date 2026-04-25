import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.article import Article
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
    encoded_query = quote_plus(f"{query} sourcelang:english")
    return (
        f"{GDELT_API_URL}?query={encoded_query}"
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
        articles = data.get("articles", [])
        filtered = [
            a for a in articles
            if a.get("language", "").lower() in ("english", "en", "")
        ]
        return filtered
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("GDELT rate limited, waiting 10s")
            await asyncio.sleep(10)
        else:
            logger.warning(f"GDELT HTTP error {e.response.status_code} for query: {query}")
        return []
    except Exception as e:
        logger.warning(f"GDELT fetch failed for query '{query}': {e}")
        return []


async def _build_search_query(topic_label: str) -> str:
    from app.services.llm import _call_llm

    result = await _call_llm(
        system_prompt=(
            "You are a search query generator. Given a news topic label, "
            "generate a focused 2-4 word search phrase for finding related news articles. "
            "Output ONLY the search phrase, nothing else. No quotes, no explanation."
        ),
        user_prompt=f"Topic: {topic_label}",
        json_mode=False,
        max_tokens=30,
    )
    if result:
        import re as _re
        cleaned = result.strip().strip('"').strip("'").strip()
        cleaned = _re.sub(r'["\'\[\]{}(),]', ' ', cleaned)
        cleaned = " ".join(cleaned.split())
        if 2 <= len(cleaned) <= 80 and cleaned.lower() not in ("search query", "news"):
            return cleaned

    tokens = topic_label.replace(" — ", " ").replace("—", " ").split()
    stop = {"the", "a", "an", "and", "or", "in", "on", "of", "for", "to",
            "is", "are", "was", "were", "has", "have", "with", "from", "at", "by"}
    keywords = [t for t in tokens if t.lower() not in stop and len(t) > 2]
    if len(keywords) < 2:
        keywords = tokens[:3]
    return " ".join(keywords[:4])


def _compute_url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()


async def _upsert_gdelt_articles(
    db_session: AsyncSession,
    cluster: Cluster,
    gdelt_articles: list[dict],
    window_start: datetime,
) -> list[uuid.UUID]:
    article_ids = []
    for a in gdelt_articles:
        url = a.get("url", "").strip()
        if not url:
            continue

        url_hash = _compute_url_hash(url)
        existing = await db_session.execute(
            select(Article.id).where(Article.url_hash == url_hash).limit(1)
        )
        row = existing.first()
        if row:
            article_ids.append(row[0])
            continue

        title = clean_text(a.get("title", "Untitled"))[:500]
        source = a.get("domain", a.get("source", "GDELT"))
        seen = a.get("seendate", "")
        published_at = _parse_gdelt_date(seen) or window_start

        article = Article(
            url=url,
            url_hash=url_hash,
            title=title,
            summary=None,
            source=source,
            published_at=published_at,
            cluster_id=cluster.id,
        )
        db_session.add(article)
        await db_session.flush()
        article_ids.append(article.id)

    return article_ids


def _parse_gdelt_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    try:
        cleaned = date_str.strip().replace("T", " ").replace("Z", "")
        if len(cleaned) == 14:
            return datetime.strptime(cleaned, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        if len(cleaned) >= 10:
            return datetime.strptime(cleaned[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass
    return None


async def _summarize_gdelt_articles(
    topic_label: str,
    articles: list[dict],
    window_start: datetime,
) -> tuple[str, str]:
    from app.services.llm import generate_commit_summary

    titles = [clean_text(a.get("title", "")) for a in articles[:8]]
    titles = [t for t in titles if t]

    result = await generate_commit_summary(topic_label, titles, titles)
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
    db_session: AsyncSession,
) -> int:
    query = await _build_search_query(cluster.topic_label)
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

            article_ids = await _upsert_gdelt_articles(
                db_session, cluster, articles, window_start,
            )

            message, detail = await _summarize_gdelt_articles(
                cluster.topic_label, articles, window_start,
            )

            commit = Commit(
                id=uuid.uuid4(),
                cluster_id=cluster.id,
                message=message,
                detail=detail,
                article_ids=article_ids,
                commit_date=window_start + timedelta(days=DAYS_PER_WINDOW // 2),
            )
            db_session.add(commit)
            commits_created += 1

    return commits_created


async def run_gdelt_backfill(db_session: AsyncSession) -> int:
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
