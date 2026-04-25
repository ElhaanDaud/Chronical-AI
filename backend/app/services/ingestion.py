import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.article import Article

RSS_FEEDS = [
    {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Reuters", "url": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best"},
    {"name": "AP News", "url": "https://feeds.apnews.com/apnews/topnews"},
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/feeds/default/rssfeed.xml"},
    {"name": "NDTV", "url": "https://feeds.ndtv.com/ndrss/news"},
]


def normalize_url(url: str) -> str:
    return url.split("?")[0].rstrip("/").lower()


def compute_url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def parse_published_date(entry: dict) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        from time import mktime
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)

    if hasattr(entry, "published") and entry.published:
        try:
            return parsedate_to_datetime(entry.published).astimezone(timezone.utc)
        except Exception:
            pass

    return datetime.now(timezone.utc)


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
                    select(Article.id).where(Article.url_hash == h)
                )
                if exists.scalar_one_or_none():
                    continue

                article = Article(
                    url=link,
                    url_hash=h,
                    title=getattr(entry, "title", "Untitled"),
                    summary=getattr(entry, "summary", None),
                    source=feed_config["name"],
                    published_at=parse_published_date(entry),
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
