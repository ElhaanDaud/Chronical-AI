# Chronicle AI — Knowledge Base

**Generated:** 2026-04-26 | **Branch:** main | **Commit:** cff512f

## Overview

News aggregation pipeline: RSS feeds → dedup → TF-IDF clustering → LexRank summarization → PostgreSQL → FastAPI → Next.js 14. Single-process, no Celery/Redis, ≤512MB RAM target.

## Structure

```
chronical-ai/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers: health, stories, search, ingest
│   │   ├── core/          # database.py (async engine), logging.py (single "chronicle" logger), limiter.py (shared slowapi Limiter)
│   │   ├── models/        # SQLAlchemy ORM: Cluster, Article, Commit
│   │   ├── schemas/       # Pydantic: StoryCard, StoryDetail, CommitResponse, CatchUpResponse, HealthResponse, ErrorResponse
│   │   ├── services/      # ingestion, clustering, summarization, lifecycle, cleanup
│   │   ├── config.py      # Pydantic Settings (env_file=".env")
│   │   └── main.py        # FastAPI app, APScheduler (3 jobs), CORS, slowapi, global exception handler
│   ├── alembic/           # Async migrations (001_initial_schema: clusters, articles, commits + tsvector trigger)
│   ├── alembic.ini
│   ├── railway.toml       # Railway deployment config
│   ├── Dockerfile         # python:3.11-slim + spaCy en_core_web_sm + nltk punkt_tab
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js 14 App Router: page.tsx (dashboard), story/[id], search
│   │   ├── components/    # StoryCard, CommitLog, CatchUpPanel, HeatBadge, SearchBar, Navbar + shadcn/ui
│   │   └── lib/           # api.ts (typed fetch wrapper), utils.ts (cn, formatRelativeTime)
│   ├── Dockerfile         # Multi-stage node:20-alpine, standalone output
│   ├── vercel.json        # Vercel deployment config
│   └── package.json
├── docker-compose.yml     # postgres:16-alpine + backend + frontend
├── .env.example
├── prompt.md              # 1100-line implementation spec (the bible)
└── orchestrator.md        # 4-phase implementation plan
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
| Add frontend page | `frontend/src/app/` | Next.js App Router, server components by default |
| Add frontend component | `frontend/src/components/` | Client components need "use client" directive |
| Modify API fetch layer | `frontend/src/lib/api.ts` | Typed fetch wrapper, server vs client base URL |

## Import Dependency Graph

```
main.py
├── app.api (api_router)
│   ├── app.api.health (get_db, Article, Cluster, HealthResponse)
│   ├── app.api.stories (get_db, Cluster, Article, Commit, StoryCard, StoryDetail, CommitResponse, CatchUpResponse)
│   ├── app.api.search (get_db, Article, SearchResult)
│   └── app.api.ingest (ingest_feeds, run_clustering, run_summarization, run_lifecycle)
├── app.config (settings)
├── app.core.database (async_session_factory)
├── app.core.logging (logger)
├── app.services.ingestion (ingest_feeds)
├── app.services.clustering (run_clustering)
├── app.services.summarization (run_summarization)
├── app.services.lifecycle (run_lifecycle)
└── app.services.cleanup (cleanup_old_articles)

app.models
├── cluster.py → defines Base (DeclarativeBase)
├── article.py → imports Base from cluster
└── commit.py  → imports Base from cluster

app.services.clustering → imports app.models, app.core.logging, sklearn, spacy
app.services.summarization → imports app.models, app.core.logging, sumy, nltk
app.services.lifecycle → imports app.models, app.core.logging, app.services.clustering (calculate_heat)
app.services.cleanup → imports app.models, app.core.logging, app.config

app.core.database → imports app.config.settings
app.core.limiter → imports slowapi (standalone, no app-level deps)
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
- **Error handling**: All scheduler jobs wrapped in try/except. API endpoints handle DB errors gracefully
- **Frontend**: Server components by default. Client components ("use client") only for interactivity (CatchUpPanel, SearchBar, StoryCard, CommitLog)

## Anti-Patterns (This Project)

- `as any`, `@ts-ignore`, `@ts-expect-error` — never
- `print()` for logging — use `logger` from `app.core.logging`
- Relative imports — absolute only
- Direct `engine.execute()` — use `AsyncSession` via `get_db` or `async_session_factory`
- Raw SQL strings for JSONB defaults in Alembic — wrap with `sa.text()`
- Adding comments to Python files — codebase is comment-free
- N+1 queries — use subqueries or joinedload for related counts
- `scalar_one_or_none()` for existence checks — use `.limit(1).first()`

## Gotchas

- **Alembic URL**: `alembic.ini` has `localhost` URL; `env.py` overrides with `settings.database_url` at runtime. When running migrations outside Docker, set `DATABASE_URL` env var
- **No .env file in repo**: Only `.env.example` exists. Docker Compose passes env vars directly. Local dev requires creating `.env` from `.env.example`
- **Ingestion commits per feed**: Each RSS feed commits independently — partial ingestion is possible on failure (by design, not a bug)
- **Dockerfile runs as root**: No `USER` instruction. Acceptable for dev, needs hardening for prod
- **spaCy model baked into image**: Changing model requires full image rebuild
- **Scheduler runs in-process**: APScheduler uses AsyncIOScheduler in FastAPI lifespan. No external job queue
- **Docker network routing**: Server-side Next.js fetches use `API_URL=http://backend:8000` (Docker service name). Client-side uses `NEXT_PUBLIC_API_URL`
- **NLTK punkt_tab**: Downloaded at build time in Dockerfile. If missing, LexRank summarization fails
- **Static prerender disabled**: Dashboard and search pages use `force-dynamic` export to avoid build-time API fetch failures

## Commands

```bash
# Start everything
docker compose up --build

# Start detached
docker compose up -d --build

# Run migrations (inside container)
docker compose exec backend alembic upgrade head

# Health check
curl http://localhost:8000/api/health

# Trigger full pipeline manually
curl -X POST "http://localhost:8000/api/ingest?full_pipeline=true"

# Rebuild from scratch (wipe DB)
docker compose down -v && docker compose up --build

# View backend logs
docker compose logs -f backend

# Connect to database
docker compose exec postgres psql -U chronicle -d chronicle_db
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
| 2026-04-25 | Phase 2 | TF-IDF/KMeans clustering, spaCy NER, heat score lifecycle, LexRank summarization | clustering.py, summarization.py, lifecycle.py, main.py, Dockerfile |
| 2026-04-25 | Phase 3 | REST API endpoints (stories, search), rate limiting, caching, Next.js frontend (dashboard, story detail, search) | stories.py, search.py, api/__init__.py, frontend/ (39 files), docker-compose.yml |
| 2026-04-25 | Phase 4 | Data retention cleanup job, Railway/Vercel deploy config, README | cleanup.py, main.py, railway.toml, vercel.json, README.md, Dockerfile |
| 2026-04-26 | Bugfix | Manual ingest endpoint, .gitignore rewrite | ingest.py, api/__init__.py, .gitignore |
| 2026-04-26 | Audit | 14 bug fixes: ORM types, N+1 query, TF-IDF perf, URL normalization, error handling, RSS feeds, lifecycle, cleanup batching | 10 backend files |
| 2026-04-26 | Enhance | HTML text cleaning, heat momentum with commit activity, topic_tokens UX (backend + frontend) | clustering.py, summarization.py, lifecycle.py, story.py, stories.py, api.ts, story-card.tsx, page.tsx |
| 2026-04-26 | Audit 2 | 7 critical/high fixes: HTMLParser crash guard, None date guard, stale selectinload refresh, search HTML sanitization, cache invalidation, updated_at on article assignment, shared rate limiter | clustering.py, search.py, ingest.py, stories.py, main.py, core/limiter.py |
