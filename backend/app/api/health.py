from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.models.article import Article
from app.models.cluster import Cluster
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    try:
        last_ingestion_result = await db.execute(
            select(func.max(Article.ingested_at))
        )
        last_ingestion = last_ingestion_result.scalar_one_or_none()

        active_stories_result = await db.execute(
            select(func.count()).select_from(Cluster).where(Cluster.state == "active")
        )
        active_stories = active_stories_result.scalar_one()

        total_articles_result = await db.execute(
            select(func.count()).select_from(Article)
        )
        total_articles = total_articles_result.scalar_one()

        status = "ok" if last_ingestion is not None else "degraded"

        return HealthResponse(
            status=status,
            last_ingestion=last_ingestion,
            active_stories=active_stories,
            total_articles=total_articles,
        )
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        return HealthResponse(
            status="degraded",
            last_ingestion=None,
            active_stories=0,
            total_articles=0,
        )
