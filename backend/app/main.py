import time
from contextlib import asynccontextmanager
from datetime import timezone as tz

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import api_router
from app.config import settings
from app.core.database import async_session_factory
from app.core.logging import logger
from app.services.cleanup import cleanup_old_articles
from app.services.clustering import run_clustering
from app.services.ingestion import ingest_feeds
from app.services.lifecycle import run_lifecycle
from app.services.summarization import run_summarization

scheduler = AsyncIOScheduler()


async def ingest_feeds_job():
    try:
        async with async_session_factory() as session:
            await ingest_feeds(session)
    except Exception as e:
        logger.exception(f"Ingestion job failed: {e}")


async def clustering_job():
    try:
        async with async_session_factory() as session:
            await run_clustering(session)
            await run_summarization(session)
            await run_lifecycle(session)
    except Exception as e:
        logger.exception(f"Clustering job failed: {e}")


async def cleanup_job():
    try:
        async with async_session_factory() as session:
            await cleanup_old_articles(session)
    except Exception as e:
        logger.exception(f"Cleanup job failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        ingest_feeds_job,
        "interval",
        minutes=settings.ingestion_interval_minutes,
        id="ingest",
        replace_existing=True,
    )
    scheduler.add_job(
        clustering_job,
        "interval",
        hours=settings.clustering_interval_hours,
        id="cluster",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_job,
        "cron",
        hour=3,
        timezone=tz.utc,
        id="cleanup",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")
    yield
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Chronicle AI",
    description="News story timelines as commit logs",
    version="0.1.0",
    lifespan=lifespan,
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        settings.frontend_url,
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_slow_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    if duration > 2.0:
        logger.warning(f"SLOW {request.method} {request.url.path} {duration:.2f}s")

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": None},
    )


app.include_router(api_router)
