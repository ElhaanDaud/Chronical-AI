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

## Local Development

### Prerequisites

- Docker + Docker Compose
- Node.js 20+ (for frontend development outside Docker)

### Quick Start

```bash
docker compose up --build
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432

Migrations run automatically on backend startup via volume mount.

### Manual Migration

```bash
docker compose exec backend alembic upgrade head
```

### Health Check

```bash
curl http://localhost:8000/api/health
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Service health + stats |
| GET | /api/stories | Active/cooling stories sorted by heat |
| GET | /api/stories/{id} | Story detail with commits |
| GET | /api/stories/{id}/commits | Paginated commit history |
| GET | /api/stories/{id}/catchup | Narrative catch-up summary |
| GET | /api/search?q= | Full-text article search |

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

BBC World, Reuters, AP News, The Hindu, NDTV. Configured in `backend/app/services/ingestion.py`.

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
- **Some RSS feeds may fail**: Reuters/AP feeds occasionally change format. Ingestion continues with remaining feeds — partial ingestion is by design.
