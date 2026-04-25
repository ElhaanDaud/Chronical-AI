# Chronicle AI — Agent Instructions

You are a senior AI/backend engineer with deep expertise in Python, FastAPI, NLP pipelines, and full-stack web development. You write production-quality, well-structured code with proper error handling, logging, and comments. You think in systems — memory constraints, failure modes, and operational simplicity come before writing any code.

Your implementation bible is `prompt.md` in the root of this repo. **Read it fully before doing anything.** It contains the complete architecture, database schema, service specifications, file structure, dependency list, and 8-week implementation timeline for Chronicle AI. Follow it exactly. Do not deviate from the stack, constraints, or simplifications documented there. When in doubt, re-read the relevant section in `prompt.md` before proceeding.

---

## Phase 1 — Foundation (Weeks 1–2)

Implement Phase 1 from `prompt.md`:

- Project scaffolding matching the file structure in `prompt.md`
- Docker Compose for local dev (FastAPI backend + PostgreSQL)
- PostgreSQL schema with Alembic migrations (all 3 tables, indexes, and the search vector trigger exactly as specified)
- FastAPI app skeleton with lifespan, config via Pydantic Settings, and async SQLAlchemy session
- RSS ingestion service (`services/ingestion.py`): feedparser, URL normalization, deduplication by URL hash, all 5 feeds
- APScheduler wired into FastAPI lifespan, ingestion job every 30 minutes
- `/health` endpoint

When Phase 1 is complete and working locally, commit all changes:

```
git add .
git commit -m "feat: initialise project structure with FastAPI, PostgreSQL schema, Alembic migrations, RSS ingestion service, and Docker Compose"
```

---

## Phase 2 — Clustering + Summaries (Weeks 3–4)

Phase 1 is complete. Now implement Phase 2 from `prompt.md`:

- Clustering service (`services/clustering.py`): TF-IDF vectorization + KMeans, spaCy NER entity extraction using `en_core_web_sm`, entity fingerprint aggregation on clusters, heat score calculation, state transitions (active → cooling → hibernated)
- Summarization service (`services/summarization.py`): LexRank via sumy to generate one-line commit messages (≤150 chars) and 3-sentence detail blocks, keyword-based topic labels from TF-IDF
- Lifecycle service (`services/lifecycle.py`): heat score decay and cluster state machine
- Wire both services into APScheduler in `main.py` — clustering every 2 hours, summarization triggered on cluster update

Stay within the ≤512 MB RAM constraint. Use `en_core_web_sm` (15 MB), not `en_core_web_trf`. No transformer models. No external queues.

When Phase 2 is complete and verified (clusters are forming, commits are generating), commit all changes:

```
git add .
git commit -m "feat: add TF-IDF/KMeans clustering pipeline, spaCy NER entity extraction, heat score lifecycle, and LexRank summarization"
```

---

## Phase 3 — API + Frontend (Weeks 5–7)

Phases 1 and 2 are complete. Now implement Phase 3 from `prompt.md`:

**Backend:**
- Complete all REST endpoints in `api/`: `/stories`, `/stories/{id}/commits`, `/catchup/{id}`, `/search`, `/health`
- CORS middleware, slowapi rate limiting, in-memory caching for the dashboard response
- Proper error handling and response schemas (Pydantic)

**Frontend:**
- Next.js 14 app with the structure defined in `prompt.md`
- Dashboard: topic cards sorted by heat score
- Story detail page: chronological commit log with source attribution
- Catch Me Up panel: template-based narrative from commits
- Full-text search across articles
- Tailwind CSS + shadcn/ui, mobile-responsive layout

Next.js handles rendering only — all data comes from the FastAPI backend. No Next.js API routes.

When Phase 3 is complete and the full flow works end-to-end locally, commit all changes:

```
git add .
git commit -m "feat: implement REST API endpoints, rate limiting, in-memory caching, and Next.js frontend with story dashboard, commit log, and full-text search"
```

---

## Phase 4 — Deploy + Polish (Week 8)

Phases 1–3 are complete and working locally. Now implement Phase 4 from `prompt.md`:

- Railway deployment config for the FastAPI backend and PostgreSQL — environment variables via Pydantic Settings, confirm startup within 512 MB RAM
- Vercel deployment for the Next.js frontend with `NEXT_PUBLIC_API_URL` pointing to the Railway backend
- Data retention cleanup job in APScheduler: prune old hibernated clusters and stale articles
- Confirm request logging middleware is in place (`core/logging.py`)
- End-to-end verification: all 5 RSS feeds ingesting, clustering producing 10–20 clusters, commits generating correctly, dashboard loading, search working
- Update README with deployment steps and any known gotchas

When Phase 4 is complete and deployed, commit all changes:

```
git add .
git commit -m "chore: configure Railway and Vercel deployment, add data retention job, request logging middleware, and update README with deployment docs"
```