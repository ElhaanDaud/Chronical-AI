from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import logger
from app.models import Article, Cluster

BATCH_SIZE = 500


async def cleanup_old_articles(db: AsyncSession):
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.article_retention_days)

        stale_ids_result = await db.execute(
            select(Article.id).where(
                Article.published_at < cutoff,
                Article.cluster_id.in_(
                    select(Cluster.id).where(Cluster.state == "hibernated")
                ),
            ).limit(BATCH_SIZE)
        )
        stale_ids = [row[0] for row in stale_ids_result.all()]

        deleted_articles = 0
        if stale_ids:
            result = await db.execute(
                delete(Article).where(Article.id.in_(stale_ids))
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
    except Exception as e:
        logger.exception(f"Cleanup failed: {e}")
        await db.rollback()
