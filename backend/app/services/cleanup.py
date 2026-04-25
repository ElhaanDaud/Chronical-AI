from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import logger
from app.models import Article, Cluster


async def cleanup_old_articles(db: AsyncSession):
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.article_retention_days)

    result = await db.execute(
        delete(Article).where(
            Article.published_at < cutoff,
            Article.cluster_id.in_(
                select(Cluster.id).where(Cluster.state == "hibernated")
            ),
        )
    )
    deleted_articles = result.rowcount

    result = await db.execute(
        delete(Cluster).where(
            Cluster.state == "hibernated",
            ~Cluster.id.in_(
                select(Article.cluster_id).where(Article.cluster_id.isnot(None))
            ),
        )
    )
    deleted_clusters = result.rowcount

    await db.commit()
    logger.info(
        f"Cleanup: removed {deleted_articles} articles and {deleted_clusters} "
        f"empty clusters older than {cutoff.date()}"
    )
