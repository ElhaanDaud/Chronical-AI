from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.search import router as search_router
from app.api.stories import router as stories_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(ingest_router, tags=["ingest"])
api_router.include_router(stories_router, tags=["stories"])
api_router.include_router(search_router, tags=["search"])
