# Chronicle AI — Knowledge Base

**Generated:** 2026-04-26 | **Branch:** main | **Commit:** 7dbb5ba

## Overview

News aggregation pipeline: RSS feeds → dedup → TF-IDF/embedding clustering → LLM coherence gate → LLM summarization → GDELT historical backfill → PostgreSQL → FastAPI → Next.js 14. Single-process, no Celery/Redis, ≤512MB RAM target.

## Structure

```
chronical-ai/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers: health, stories, search, ingest
│   │   ├── core/          # database.py (async engine), logging.py (single "chronicle" logger), limiter.py (shared slowapi Limiter)
│   │   ├── models/        # SQLAlchemy ORM: Cluster, Article, Commit
│   │   ├── schemas/       # Pydantic: StoryCard, StoryDetail, CommitResponse, CatchUpResponse, HealthResponse, ErrorResponse
│   │   ├── services/      # ingestion, clustering, summarization, lifecycle, cleanup, llm, gdelt
│   │   ├── config.py      # Pydantic Settings (env_file=".env") — includes LLM/embedding config
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
├── docker-compose.yml     # postgres:16-alpine + backend + frontend (extra_hosts for DMR)
├── .env.example
├── prompt.md              # 1100-line implementation spec (the bible)
└── orchestrator.md        # 7-phase frontend redesign plan (Editorial Intelligence design system)
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
│   └── app.api.ingest (ingest_feeds, run_clustering, run_summarization, run_lifecycle, run_gdelt_backfill)
├── app.config (settings)
├── app.core.database (async_session_factory)
├── app.core.logging (logger)
├── app.services.ingestion (ingest_feeds)
├── app.services.clustering (run_clustering)
├── app.services.summarization (run_summarization)
├── app.services.lifecycle (run_lifecycle)
└── app.services.cleanup (cleanup_old_articles)
└── app.services.gdelt (run_gdelt_backfill)

app.models
├── cluster.py → defines Base (DeclarativeBase)
├── article.py → imports Base from cluster
└── commit.py  → imports Base from cluster

app.services.clustering → imports app.models, app.core.logging, sklearn, spacy
app.services.summarization → imports app.models, app.core.logging, sumy, nltk
app.services.lifecycle → imports app.models, app.core.logging, app.services.clustering (calculate_heat)
app.services.cleanup → imports app.models, app.core.logging, app.config
app.services.llm → imports app.config, app.core.logging, openai (AsyncOpenAI), numpy
app.services.gdelt → imports app.core.logging, app.models.cluster, app.models.commit, app.services.clustering (clean_text), app.services.llm, httpx

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
- **Frontend Design System**: Newsreader (serif, headlines) + Inter (sans, body/UI). Material Symbols Outlined icons via `<MaterialIcon>` component. Editorial Intelligence color palette (CSS variables in globals.css). 4px spacing base unit. No hardcoded hex in components — always CSS variables via Tailwind
- **Frontend Orchestrator**: All frontend redesign phases documented in `orchestrator.md`. Reference designs in `/stitch_chronicle_ai_product_interface/` (6 HTML + 6 screenshots + 2 DESIGN.md)

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
- **Docker Model Runner (DMR)**: Works on Docker Desktop (implicit networking) or Docker Engine (`docker-model-plugin` package, port 12434, `extra_hosts` in compose). Models run on host, not in backend container. Config in `config.py` (llm_base_url, embedding_base_url)
- **DMR cold start**: First request loads model into memory (5-15s). Rapid pipeline requests during cold start cause LLM fallback to LexRank/TF-IDF
- **Llama 3.2 1B JSON compliance**: 1B model sometimes parrots prompt examples or outputs malformed JSON. `llm.py` has regex fallback parsing and rejects template values
- **GDELT API quirks**: Returns HTML error pages for some queries (causes JSON parse failure). `sourcelang:english` filter is unreliable — post-fetch language filtering required. Rate limited at ~1 req/s. Query must be URL-encoded via `quote_plus`

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
| 2026-04-26 | LLM | Docker Model Runner integration: llm.py service (DMR + Groq dual-provider), LLM coherence gate, LLM topic labels, LLM commit summaries, dense embeddings via qwen3 | llm.py, clustering.py, summarization.py, config.py, docker-compose.yml, requirements.txt |
| 2026-04-26 | DMR Setup | Docker Engine DMR config: port 12434, extra_hosts networking, prompt hardening for Llama 3.2 1B JSON compliance | config.py, docker-compose.yml, .env.example, llm.py |
| 2026-04-26 | GDELT | GDELT Doc API historical backfill (20 days, English), asyncio.gather parallel LLM calls, prompt caching, DMR thread tuning (8 threads, batch 1024) | gdelt.py, clustering.py, llm.py, main.py, ingest.py |
| 2026-04-26 | GDELT Fix | GDELT backfill creates Article rows (source_urls populated), LLM search query generation, post-fetch English filter, URL encoding, cache invalidation after backfill | gdelt.py, main.py |
| 2026-04-27 | Frontend Redesign Plan | Complete frontend redesign orchestrator: 7 phases (P0-P6), Editorial Intelligence design system (Newsreader+Inter fonts, Paper&Ink light + Navy dark palettes, 4px spacing, Material Symbols), gap analysis, component specs for dashboard/story-detail/search, AGENTS.md updated with frontend conventions | orchestrator.md, AGENTS.md |
