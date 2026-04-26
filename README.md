# Chronicle AI

News aggregation pipeline that tracks evolving stories as git-style commit logs.

RSS feeds → TF-IDF + dense embeddings clustering → LLM coherence gate → LLM-generated summaries → GDELT historical backfill → PostgreSQL → FastAPI → Next.js 14

## Architecture

| Component | Stack | Role |
|-----------|-------|------|
| Backend | FastAPI + APScheduler | REST API, ingestion, clustering, summarization |
| Frontend | Next.js 14, Tailwind, shadcn/ui | Dashboard, story detail, search |
| Database | PostgreSQL 16 | Articles, clusters, commits, full-text search |
| LLM (primary) | Docker Model Runner (ai/llama3.2:1B-Q4_0) | Topic labels, coherence scoring, commit summaries |
| Embeddings | Docker Model Runner (ai/qwen3-embedding:0.6B-F16) | Dense semantic similarity for clustering |
| LLM (fallback) | Groq API (llama-3.1-8b-instant) | Fallback when DMR unavailable |
| Historical data | GDELT Doc API | Backfills 20-day commit history per cluster (English only) |

Single process. No Celery, no Redis. LLM runs via Docker Model Runner (host-side) or Groq API — not inside the backend container.

## Prerequisites

- Docker + Docker Compose
- Docker Model Runner — works with **Docker Desktop** (enable in AI settings) **or Docker Engine** (install `docker-model-plugin` package)
- Groq API key (free tier at https://console.groq.com) — required as fallback if DMR unavailable
- Node.js 20+ (only for frontend development outside Docker)

### Install Docker Model Runner (Docker Engine — no Docker Desktop needed)

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install docker-model-plugin

# RPM-based (Fedora, RHEL)
sudo dnf update && sudo dnf install docker-model-plugin

# Install the inference runner
docker model install-runner

# Pull required models
docker model pull ai/llama3.2:1B-Q4_0
docker model pull ai/qwen3-embedding:0.6B-F16

# Verify
docker model ls
curl http://localhost:12434/engines/v1/models
```

> **Note**: On Docker Engine, DMR serves on port 12434 (TCP enabled by default). Containers reach DMR via `extra_hosts: ["model-runner.docker.internal:host-gateway"]` in docker-compose.yml. On Docker Desktop, port is implicit and `model-runner.docker.internal` resolves automatically.

## Quick Start

```bash
# Clone and start all services (postgres + backend + frontend)
docker compose up --build

# Wait for health check to pass, then open:
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# Postgres:  localhost:5432
```

Migrations run automatically on backend startup.

## Environment Setup

Copy `.env.example` to `backend/.env` and fill in your Groq API key:

```bash
cp .env.example backend/.env
# Edit backend/.env — set GROQ_API_KEY=gsk_...
```

If using Docker Model Runner, set `LLM_PROVIDER=dmr` in `.env`. Otherwise keep `LLM_PROVIDER=groq` (default).

## Running Commands

### Start / Stop / Rebuild

```bash
# Start all services (detached)
docker compose up -d --build

# Stop all services
docker compose down

# Stop and wipe database (fresh start)
docker compose down -v && docker compose up -d --build

# Rebuild only backend (after code changes)
docker compose build backend && docker compose up -d backend

# Rebuild only frontend
docker compose build frontend && docker compose up -d frontend

# View logs (all services)
docker compose logs -f

# View logs (single service)
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
```

### Database

```bash
# Run migrations manually
docker compose exec backend alembic upgrade head

# Check migration history
docker compose exec backend alembic history

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Connect to database directly
docker compose exec postgres psql -U chronicle -d chronicle
```

### Ingestion & Pipeline

```bash
# Trigger manual ingestion (fetch RSS feeds only)
curl -X POST http://localhost:8000/api/ingest

# Trigger full pipeline (ingest + cluster + summarize + lifecycle)
curl -X POST "http://localhost:8000/api/ingest?full_pipeline=true"

# Check health / stats
curl http://localhost:8000/api/health
```

### Frontend Development (outside Docker)

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000

# Build for production
npm run build
npm run start
```

### Backend Development (outside Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

# Set DATABASE_URL to your local postgres
export DATABASE_URL="postgresql+asyncpg://chronicle:chronicle_dev@localhost:5432/chronicle"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Service health + stats |
| GET | /api/stories | Active/cooling stories sorted by heat (5min cache) |
| GET | /api/stories/{id} | Story detail with commits |
| GET | /api/stories/{id}/commits | Paginated commit history (?limit=&offset=) |
| GET | /api/stories/{id}/catchup | Narrative catch-up summary |
| GET | /api/search?q=&limit=&offset= | Full-text article search |
| POST | /api/ingest | Manual ingestion trigger (?full_pipeline=true) |

Rate limit: 30 requests/minute on /api/stories.

## Production Deployment

### Backend (Railway)

1. Create a Railway project with PostgreSQL plugin
2. Connect the repository, set root directory to `backend/`
3. Railway reads `railway.toml` for build/deploy config
4. Set environment variables:
   - `DATABASE_URL` — provided by Railway PostgreSQL plugin
   - `FRONTEND_URL` — your Vercel deployment URL

The backend runs migrations on startup (`alembic upgrade head`) before starting uvicorn.

### Frontend (Vercel)

1. Import the repository on Vercel
2. Set root directory to `frontend/`
3. Set environment variables:
   - `NEXT_PUBLIC_API_URL` — Railway backend URL (e.g., `https://chronicle-backend.up.railway.app`)
   - `API_URL` — same as above (used for server-side rendering)

### Environment Variables

| Variable | Where | Required | Default |
|----------|-------|----------|---------|
| DATABASE_URL | Backend | Yes | localhost dev URL |
| FRONTEND_URL | Backend | No | http://localhost:3000 |
| GROQ_API_KEY | Backend | Yes (if LLM_PROVIDER=groq) | — |
| LLM_PROVIDER | Backend | No | groq |
| LLM_MODEL | Backend | No | ai/llama3.2:1B-Q4_0 |
| LLM_BASE_URL | Backend | No | http://model-runner.docker.internal:12434/engines/v1 |
| EMBEDDING_MODEL | Backend | No | ai/qwen3-embedding:0.6B-F16 |
| EMBEDDING_BASE_URL | Backend | No | http://model-runner.docker.internal:12434/engines/llama.cpp/v1 |
| NEXT_PUBLIC_API_URL | Frontend | Yes | http://localhost:8000 |
| API_URL | Frontend | No | falls back to NEXT_PUBLIC_API_URL |

## Background Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Ingestion | Every 30 min | Fetch RSS feeds, deduplicate by URL hash |
| Clustering | Every 2 hours | TF-IDF + KMeans clustering, NER, heat score, summarization, GDELT backfill |
| Cleanup | Daily 3 AM UTC | Prune articles >30 days in hibernated clusters |

## RSS Feeds

BBC World, Reuters, The Hindu, NDTV, NPR, Al Jazeera. Configured in `backend/app/services/ingestion.py`.

## Clustering Pipeline

1. **HTML cleaning**: Strip HTML tags, scripts, URLs from RSS content using stdlib HTMLParser
2. **Pass 1**: Dense embeddings (Qwen3 0.6B via DMR) or TF-IDF cosine similarity + Jaccard entity overlap against existing clusters. Threshold: 0.55
3. **Pass 2**: MiniBatchKMeans on unmatched articles (min 3 articles per cluster, max 25 clusters)
4. **LLM coherence gate**: Each new cluster scored 0.0–1.0 by LLM. Rejected if below 0.4
5. **Topic labels**: LLM-generated from article titles (fallback: TF-IDF top-4 keywords)
6. **NER**: spaCy `en_core_web_sm` extracts PERSON/ORG/GPE/EVENT entities
7. **Heat score**: H(t) = Σ e^(-0.15 × Δt) + 0.5 × commits_last_10_days
8. **States**: active (≥3.0) → cooling (≥1.0) → hibernated (<1.0 for 3+ days)
9. **Summarization**: LLM-generated commit messages and details (fallback: LexRank via sumy)
10. **GDELT backfill**: Fetches English-language articles from GDELT Doc API for the past 20 days per cluster topic, creating backdated commits to build a timeline of story evolution
11. **LLM parallelism**: Coherence + label checks run concurrently via asyncio.gather with semaphore (6 concurrent)
12. **Prompt caching**: Identical LLM prompts are cached for 10 minutes (md5 hash key) to avoid redundant API calls
13. **DMR tuning**: llama.cpp runtime configured with 8 threads and batch_size 1024 for faster inference

## Known Gotchas

- **Alembic URL**: `alembic.ini` has localhost; `env.py` overrides with `settings.database_url` at runtime. Set `DATABASE_URL` env var when running migrations outside Docker.
- **NLTK data**: `punkt_tab` tokenizer is downloaded at Docker build time. If missing, summarization fails silently.
- **spaCy model**: `en_core_web_sm` (15 MB) is baked into the Docker image. Changing model requires rebuild.
- **Railway RAM**: ≤512 MB. The `en_core_web_sm` model + TF-IDF vectorizer fit within limits. LLM runs outside the backend container (Docker Model Runner or Groq API). Do not use `en_core_web_trf` (500 MB).
- **Docker network**: Server-side Next.js fetches use `API_URL=http://backend:8000` (Docker service name). Client-side uses `NEXT_PUBLIC_API_URL` (public URL).
- **Docker Model Runner**: Works with Docker Desktop (enable Model Runner in AI settings) or Docker Engine (install `docker-model-plugin`). On Docker Engine, DMR listens on port 12434 and containers need `extra_hosts: ["model-runner.docker.internal:host-gateway"]`. Models run on the host, not inside containers. Falls back to Groq if unavailable.
- **DMR cold start**: First LLM request after model pull loads the model into memory (5-15s). Subsequent requests are fast. If the pipeline runs before the model is warm, some commit messages may fall back to LexRank.
- **Llama 3.2 1B limitations**: The 1B model occasionally generates poor JSON or parrots prompt examples. The code has regex fallback parsing and rejects template-parroted values like "short update".
- **RSS feed resilience**: Some feeds occasionally change format. Ingestion continues with remaining feeds — partial ingestion is by design.
- **LLM fallback chain**: DMR primary → Groq fallback (or vice versa based on LLM_PROVIDER). If both fail, clustering uses TF-IDF labels and LexRank summaries.
- **GDELT rate limits**: GDELT Doc API returns 429 on heavy use. Backfill sleeps 1s between windows and 10s on rate limit. Some windows may return empty/non-JSON responses (logged as warnings, not failures).
- **GDELT backfill timing**: First full pipeline run creates GDELT commits for all clusters with <4 commits. Subsequent runs only backfill new clusters. ~15-25 minutes for 15 clusters due to API rate limits.
