from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.services.clustering import run_clustering
from app.services.ingestion import ingest_feeds
from app.services.lifecycle import run_lifecycle
from app.services.summarization import run_summarization

router = APIRouter()


@router.post("/ingest")
async def trigger_ingest(
    full_pipeline: bool = False,
    db: AsyncSession = Depends(get_db),
):
    logger.info("Manual ingestion triggered")
    await ingest_feeds(db)

    if full_pipeline:
        logger.info("Running full pipeline: clustering → summarization → lifecycle")
        await run_clustering(db)
        await run_summarization(db)
        await run_lifecycle(db)

    return {"status": "ok", "full_pipeline": full_pipeline}
