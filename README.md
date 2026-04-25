# Chronicle AI

News aggregation pipeline that tracks evolving stories as git-style commit logs.

RSS feeds → TF-IDF/KMeans clustering → spaCy NER entity linking → LexRank summarization → PostgreSQL → FastAPI → Next.js 14

## Architecture

| Component | Stack | Role |
|-----------|-------|------|
| Backend | FastAPI + APScheduler | REST API, ingestion, clustering, summarization |
| Frontend | Next.js 14, Tailwind, shadcn/ui | Dashboard, story detail, search |
| Database | PostgreSQL 16 | Articles, clusters, commits, full-text search |

Single process. No Celery, no Redis, no external AI APIs.

## Prerequisites

- Docker + Docker Compose
- Node.js 20+ (only for frontend development outside Docker)

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
docker compose exec postgres psql -U chronicle -d chronicle_db
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
export DATABASE_URL="postgresql+asyncpg://chronicle:chronicle@localhost:5432/chronicle_db"

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
| NEXT_PUBLIC_API_URL | Frontend | Yes | http://localhost:8000 |
| API_URL | Frontend | No | falls back to NEXT_PUBLIC_API_URL |

## Background Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Ingestion | Every 30 min | Fetch RSS feeds, deduplicate by URL hash |
| Clustering | Every 2 hours | TF-IDF + KMeans clustering, NER, heat score, summarization |
| Cleanup | Daily 3 AM UTC | Prune articles >30 days in hibernated clusters |

## RSS Feeds

BBC World, Reuters, The Hindu, NDTV, NPR, Al Jazeera. Configured in `backend/app/services/ingestion.py`.

## Clustering Pipeline

1. **Pass 1**: Cosine similarity (TF-IDF) + Jaccard entity overlap against existing clusters. Threshold: 0.3
2. **Pass 2**: MiniBatchKMeans on unmatched articles (min 3 articles per cluster, max 25 clusters)
3. **NER**: spaCy `en_core_web_sm` extracts PERSON/ORG/GPE/EVENT entities
4. **Heat score**: H(t) = Σ e^(-0.15 × Δt) — exponential decay per article age
5. **States**: active (≥3.0) → cooling (≥1.0) → hibernated (<1.0 for 3+ days)
6. **Summarization**: LexRank via sumy — 3-sentence extractive summary per commit

## Known Gotchas

- **Alembic URL**: `alembic.ini` has localhost; `env.py` overrides with `settings.database_url` at runtime. Set `DATABASE_URL` env var when running migrations outside Docker.
- **NLTK data**: `punkt_tab` tokenizer is downloaded at Docker build time. If missing, summarization fails silently.
- **spaCy model**: `en_core_web_sm` (15 MB) is baked into the Docker image. Changing model requires rebuild.
- **Railway RAM**: ≤512 MB. The `en_core_web_sm` model + TF-IDF vectorizer fit within limits. Do not use `en_core_web_trf` (500 MB).
- **Docker network**: Server-side Next.js fetches use `API_URL=http://backend:8000` (Docker service name). Client-side uses `NEXT_PUBLIC_API_URL` (public URL).
- **RSS feed resilience**: Some feeds occasionally change format. Ingestion continues with remaining feeds — partial ingestion is by design.
