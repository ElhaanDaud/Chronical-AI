from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.article import Article
from app.schemas.story import SearchResult
from app.services.clustering import clean_text

router = APIRouter()


@router.get("/search", response_model=list[SearchResult])
async def search_articles(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[SearchResult]:
    ts_query = func.plainto_tsquery("english", q)

    result = await db.execute(
        select(Article)
        .where(Article.search_vector.op("@@")(ts_query))
        .order_by(func.ts_rank(Article.search_vector, ts_query).desc())
        .limit(limit)
        .offset(offset)
    )
    articles = result.scalars().all()

    return [
        SearchResult(
            id=a.id,
            title=a.title,
            summary=clean_text(a.summary),
            source=a.source,
            published_at=a.published_at,
            cluster_id=a.cluster_id,
        )
        for a in articles
    ]
