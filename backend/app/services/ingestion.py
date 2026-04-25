import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urlunparse

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.article import Article

RSS_FEEDS = [
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Reuters", "url": "https://reutersbest.com/feed/"},
    {"name": "The Hindu", "url": "https://www.thehindu.com/feeder/default.rss"},
    {"name": "NDTV", "url": "https://feeds.feedburner.com/ndtvnews-top-stories"},
    {"name": "NPR", "url": "https://feeds.npr.org/1001/rss.xml"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
]


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/"),
        parsed.params,
        parsed.query,
        "",
    ))
    return normalized


def compute_url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def parse_published_date(entry: dict) -> datetime | None:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        from time import mktime
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)

    if hasattr(entry, "published") and entry.published:
        try:
            return parsedate_to_datetime(entry.published).astimezone(timezone.utc)
        except Exception:
            pass

    return None


async def ingest_feeds(db: AsyncSession) -> int:
    total_new = 0

    for feed_config in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_config["url"])
            new_in_feed = 0

            for entry in feed.entries:
                link = getattr(entry, "link", None)
                if not link:
                    continue

                h = compute_url_hash(link)
                exists = await db.execute(
                    select(Article.id).where(Article.url_hash == h).limit(1)
                )
                if exists.first():
                    continue

                published = parse_published_date(entry)
                if published is None:
                    published = datetime.now(timezone.utc)

                article = Article(
                    url=link,
                    url_hash=h,
                    title=getattr(entry, "title", "Untitled"),
                    summary=getattr(entry, "summary", None),
                    source=feed_config["name"],
                    published_at=published,
                )
                db.add(article)
                new_in_feed += 1

            await db.commit()
            total_new += new_in_feed

            if new_in_feed > 0:
                logger.info(f"Ingested {new_in_feed} new articles from {feed_config['name']}")

        except Exception as e:
            logger.error(f"Failed to ingest {feed_config['name']}: {e}")
            await db.rollback()

    logger.info(f"Ingestion complete: {total_new} new articles total")
    return total_new
