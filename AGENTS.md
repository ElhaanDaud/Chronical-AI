# Chronicle AI — Knowledge Base

**Generated:** 2026-04-25 | **Branch:** main | **Commit:** d773bcb

## Overview

News aggregation pipeline: RSS feeds → dedup → TF-IDF clustering → LexRank summarization → PostgreSQL → FastAPI → Next.js 14. Single-process, no Celery/Redis, ≤512MB RAM target.

## Structure

```
chronical-ai/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers (health only, Phase 1)
│   │   ├── core/          # database.py (async engine), logging.py (single "chronicle" logger)
│   │   ├── models/        # SQLAlchemy ORM: Cluster, Article, Commit
│   │   ├── schemas/       # Pydantic: StoryCard, StoryDetail, CommitResponse, CatchUpResponse, HealthResponse, ErrorResponse
│   │   ├── services/      # ingestion.py (RSS fetch + URL hash dedup)
│   │   ├── config.py      # Pydantic Settings (env_file=".env")
│   │   └── main.py        # FastAPI app, APScheduler, CORS, slowapi, global exception handler
│   ├── alembic/           # Async migrations (001_initial_schema: clusters, articles, commits + tsvector trigger)
│   ├── alembic.ini
│   ├── Dockerfile         # python:3.11-slim + spaCy en_core_web_sm
│   └── requirements.txt
├── docker-compose.yml     # postgres:16-alpine + backend
├── .env.example
└── prompt.md              # 1100-line implementation spec (the bible)
```

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `backend/app/api/` | Create router, wire in `api/__init__.py` |
| Add ORM model | `backend/app/models/` | Import Base from `cluster.py`, re-export in `__init__.py` |
| Add Pydantic schema | `backend/app/schemas/` | Re-export in `__init__.py` |
| Add background service | `backend/app/services/` | Receives `AsyncSession` as param, not DI |
| Change DB schema | `backend/alembic/versions/` | Alembic async migrations |
| Modify app config | `backend/app/config.py` | Pydantic Settings, env vars override defaults |
| Adjust scheduled jobs | `backend/app/main.py` | APScheduler in lifespan context manager |

## Import Dependency Graph

```
main.py
├── app.api (api_router)
│   └── app.api.health (get_db, Article, Cluster, HealthResponse)
├── app.config (settings)
├── app.core.database (async_session_factory)
├── app.core.logging (logger)
└── app.services.ingestion (ingest_feeds)

app.models
├── cluster.py → defines Base (DeclarativeBase)
├── article.py → imports Base from cluster
└── commit.py  → imports Base from cluster

app.core.database → imports app.config.settings
```

No circular dependencies. Base lives in `cluster.py` — all models import from there.

## Conventions

- **Imports**: Absolute only (`from app.core.logging import logger`)
- **Typing**: Python 3.11+ unions (`str | None`), SQLAlchemy `Mapped[]` types
- **DB sessions**: Endpoints use `Depends(get_db)`. Services receive `AsyncSession` as explicit param
- **Logging**: Single `chronicle` logger via `app.core.logging.logger`. No `print()` statements
- **Config**: Pydantic `BaseSettings` with `env_file=".env"`. Environment vars override defaults
- **Models**: `__tablename__` = pluralized. UUID primary keys. JSONB defaults via `sa.text("'[]'::jsonb")`
- **No comments in code**: Codebase is comment-free by design. Code should be self-documenting
- **Migration defaults**: Use `sa.text()` wrapper for JSONB server_default (asyncpg double-escapes raw strings)

## Anti-Patterns (This Project)

- `as any`, `@ts-ignore`, `@ts-expect-error` — never
- `print()` for logging — use `logger` from `app.core.logging`
- Relative imports — absolute only
- Direct `engine.execute()` — use `AsyncSession` via `get_db` or `async_session_factory`
- Raw SQL strings for JSONB defaults in Alembic — wrap with `sa.text()`
- Adding comments to Python files — codebase is comment-free

## Gotchas

- **Alembic URL**: `alembic.ini` has `localhost` URL; `env.py` overrides with `settings.database_url` at runtime. When running migrations outside Docker, set `DATABASE_URL` env var
- **No .env file in repo**: Only `.env.example` exists. Docker Compose passes env vars directly. Local dev requires creating `.env` from `.env.example`
- **Ingestion commits per feed**: Each RSS feed commits independently — partial ingestion is possible on failure (by design, not a bug)
- **Dockerfile runs as root**: No `USER` instruction. Acceptable for dev, needs hardening for prod
- **spaCy model baked into image**: Changing model requires full image rebuild
- **Scheduler runs in-process**: APScheduler uses AsyncIOScheduler in FastAPI lifespan. No external job queue

## Commands

```bash
# Start everything
docker compose up --build

# Run migrations (inside container)
docker compose exec backend alembic upgrade head

# Health check
curl http://localhost:8000/api/health

# Rebuild from scratch
docker compose down -v && docker compose up --build
```

## Spec Reference

All implementation decisions flow from `prompt.md`. When in doubt, check the spec. Key sections:
- Database schema: lines ~100-200
- API endpoints: lines ~300-400
- Service layer: lines ~500-700
- Phase breakdown: lines ~800-1100

---

## Change Log

| Date | Phase | Changes | Files Touched |
|------|-------|---------|---------------|
| 2026-04-25 | Phase 1 | Initial backend scaffold: Docker, DB, models, schemas, ingestion, health endpoint, Alembic migrations | All 28 files created |
