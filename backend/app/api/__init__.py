from fastapi import APIRouter, Depends

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.search import router as search_router
from app.api.stories import router as stories_router
from app.core.auth import current_active_user

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(
	ingest_router,
	tags=["ingest"],
	dependencies=[Depends(current_active_user)],
)
api_router.include_router(
	stories_router,
	tags=["stories"],
	dependencies=[Depends(current_active_user)],
)
api_router.include_router(
	search_router,
	tags=["search"],
	dependencies=[Depends(current_active_user)],
)
