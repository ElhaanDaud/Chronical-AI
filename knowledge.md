# Chronicle AI — Complete Project Knowledge Base

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Models](#data-models)
4. [Backend Services](#backend-services)
5. [API Reference](#api-reference)
6. [Scheduler & Orchestration](#scheduler--orchestration)
7. [LLM Integration](#llm-integration)
8. [Frontend Architecture](#frontend-architecture)
9. [Design System](#design-system)
10. [Configuration & Environment](#configuration--environment)
11. [Docker & Deployment](#docker--deployment)
12. [Database Migrations](#database-migrations)
13. [Dependencies](#dependencies)
14. [Data Flow Diagrams](#data-flow-diagrams)
15. [Key Constants & Thresholds](#key-constants--thresholds)
16. [Error Handling Patterns](#error-handling-patterns)
17. [Anti-Patterns](#anti-patterns)
18. [Gotchas](#gotchas)

---

## Overview

Chronicle AI is a news aggregation and intelligence platform that treats evolving news stories like version-controlled code — each story is a "cluster" of articles, and meaningful changes produce "commits" with summaries. The system ingests RSS feeds, deduplicates articles, clusters them by topic using TF-IDF/embeddings + NER, generates narrative summaries via LLM (with LexRank fallback), backfills historical context from GDELT, and presents everything through an editorial-grade Next.js frontend.

**Core Metaphor**: News stories as git repositories. Articles are source material. Clusters are repos. Commits are changelog entries tracking how a story evolves over time.

**Stack**: Python 3.11 (FastAPI) → PostgreSQL 16 → Next.js 14 (App Router). Single-process, no Celery/Redis, ≤512MB RAM target.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  Next.js 14 App Router (port 3000)                         │
│  ┌──────────┐ ┌──────────────┐ ┌────────────┐             │
│  │ Dashboard │ │ Story Detail │ │   Search   │             │
│  │ (SSR)    │ │ (SSR)        │ │ (SSR)      │             │
│  └────┬─────┘ └──────┬───────┘ └─────┬──────┘             │
│       │               │               │                     │
│       └───────────────┼───────────────┘                     │
│                       │                                     │
│              fetch(SERVER_API_BASE)                          │
└───────────────────────┼─────────────────────────────────────┘
                        │ HTTP
┌───────────────────────┼─────────────────────────────────────┐
│                    BACKEND                                   │
│  FastAPI (port 8000)                                        │
│  ┌──────────────────────────────────────────┐               │
│  │              API Layer                    │               │
│  │  /api/health  /api/stories  /api/search  │               │
│  │  /api/ingest                              │               │
│  └──────────────────┬───────────────────────┘               │
│                     │                                        │
│  ┌──────────────────┼───────────────────────┐               │
│  │           Service Layer                   │               │
│  │  Ingestion → Clustering → Summarization  │               │
│  │  Lifecycle    Cleanup      GDELT         │               │
│  │                   │                       │               │
│  │              LLM Service                  │               │
│  │         (DMR + Groq fallback)             │               │
│  └──────────────────┬───────────────────────┘               │
│                     │                                        │
│  ┌──────────────────┼───────────────────────┐               │
│  │           APScheduler                     │               │
│  │  Ingest: every 30min                      │               │
│  │  Cluster: every 2hr                       │               │
│  │  Cleanup: daily 03:00 UTC                 │               │
│  └──────────────────────────────────────────┘               │
└───────────────────────┬─────────────────────────────────────┘
                        │ asyncpg
┌───────────────────────┼─────────────────────────────────────┐
│              PostgreSQL 16 (port 5432)                       │
│  Tables: clusters, articles, commits                        │
│  Full-text search: tsvector + GIN index                     │
│  Trigger: auto-update search_vector on article changes      │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Cluster (table: `clusters`)

Represents a news story — a semantic grouping of related articles.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | UUID | uuid4 | Primary key |
| topic_label | String(500) | — | LLM-generated or TF-IDF-derived label |
| state | String(20) | "active" | Constraint: active / cooling / hibernated |
| heat_score | Float | 0.0 | Recency-weighted activity metric |
| entity_fingerprint | JSONB | [] | Named entities (PERSON, ORG, GPE, EVENT) |
| created_at | DateTime(tz) | now() | Server default |
| updated_at | DateTime(tz) | now() | Auto-updates on change |
| last_article_at | DateTime(tz) | null | Timestamp of most recent article assignment |

**Relationships**: `articles` (one-to-many), `commits` (one-to-many, cascade delete)

**State machine**:
- `active`: heat_score ≥ 3.0
- `cooling`: heat_score ≥ 1.0 but < 3.0
- `hibernated`: heat_score < 1.0 AND no new articles for 3+ days

### Article (table: `articles`)

Individual news articles ingested from RSS feeds or GDELT.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | UUID | uuid4 | Primary key |
| url | String(2048) | — | Unique, not null |
| url_hash | String(64) | — | SHA-256 of normalized URL, unique |
| title | Text | — | Not null |
| summary | Text | null | Article excerpt/description |
| source | String(255) | — | Feed source name |
| published_at | DateTime(tz) | — | Original publication date |
| ingested_at | DateTime(tz) | now() | When Chronicle ingested it |
| entities | JSONB | [] | Extracted NER entities |
| cluster_id | UUID (FK) | null | Assigned cluster, nullable |
| search_vector | TSVECTOR | null | Full-text search vector |
| created_at | DateTime(tz) | now() | Server default |

**Indexes**: published_at DESC, cluster_id, search_vector (GIN)
**Trigger**: `trg_articles_search` auto-updates search_vector from title + summary on INSERT/UPDATE

### Commit (table: `commits`)

Changelog entries for clusters — narrative summaries of story developments.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | UUID | uuid4 | Primary key |
| cluster_id | UUID (FK) | — | Not null, cascade delete |
| message | String(150) | — | Short summary headline |
| detail | Text | — | Full narrative summary |
| article_ids | ARRAY(UUID) | — | UUIDs of articles included |
| commit_date | DateTime(tz) | — | When this development occurred |
| created_at | DateTime(tz) | now() | Server default |

**Indexes**: cluster_id, commit_date DESC

### Pydantic Schemas

```
StoryCard         → id, topic_label, topic_tokens, latest_commit_message, heat_score, state, article_count, last_updated
StoryDetail       → id, topic_label, topic_tokens, state, heat_score, article_count, commits[], entity_fingerprint, created_at, updated_at
CommitResponse    → id, message, detail, commit_date, source_count, source_urls
CatchUpResponse   → story_id, narrative, commit_count, time_span_days
SearchResult      → id, title, summary, source, published_at, cluster_id
HealthResponse    → status, last_ingestion, active_stories, total_articles
ErrorResponse     → error, detail
```

---

## Backend Services

### Ingestion (`backend/app/services/ingestion.py`)

Fetches RSS feeds, deduplicates articles, and creates Article rows.

**Entry point**: `async def ingest_feeds(db: AsyncSession) -> int`

**Algorithm**:
1. Iterate over RSS_FEEDS list (BBC World, Reuters, The Hindu, NDTV, NPR, Al Jazeera)
2. Parse each feed with `feedparser`
3. For each entry: normalize URL → SHA-256 hash → check for existing url_hash
4. If new: create Article with title, summary, source, published_at, url_hash
5. Commit per feed (partial ingestion on failure is by design)

**Helpers**:
- `normalize_url(url)` → canonical form (lowercased scheme/netloc, trimmed path)
- `compute_url_hash(url)` → SHA-256 of normalized URL
- `parse_published_date(entry)` → datetime from feed entry, UTC-normalized

**Error handling**: Per-feed try/except; on failure, rollback that feed, continue others.

---

### Clustering (`backend/app/services/clustering.py`)

Assigns unclustered articles to existing clusters or creates new ones.

**Entry point**: `async def run_clustering(db: AsyncSession) -> int`

**Algorithm**:
1. Fetch all articles where `cluster_id IS NULL`
2. For each: build text snippet (title + cleaned summary), extract NER entities via spaCy
3. Load existing active/cooling clusters with their articles and commits
4. **If existing clusters**:
   - Compute embeddings for cluster texts + article texts (LLM embeddings, fallback to TF-IDF)
   - Build cosine similarity matrix between articles and clusters
   - Combined score: `0.7 × similarity + 0.3 × entity_overlap` (Jaccard)
   - If best score ≥ SIMILARITY_THRESHOLD (0.55): assign to cluster
   - Else: collect as unmatched
5. **If unmatched ≥ MIN_ARTICLES_TO_CLUSTER (3)**:
   - KMeans clustering (MiniBatchKMeans) on embeddings or TF-IDF
   - For each candidate group: LLM coherence check (threshold 0.4)
   - Derive topic_label via LLM (fallback: TF-IDF keyword extraction)
   - Create new Cluster rows with aggregated entities, heat scores
6. Refresh existing cluster heat scores and commit

**Key functions**:
- `clean_text(html)` → strips HTML tags, scripts, styles, normalizes whitespace
- `extract_entities(text)` → spaCy NER (PERSON, ORG, GPE, EVENT)
- `entity_overlap_score(a, b)` → Jaccard-like set overlap
- `calculate_heat(articles, commits)` → exponential decay (λ=0.15) weighted by recency + commit activity
- `_get_article_embeddings(texts)` → dense embeddings via LLM service
- `_llm_topic_label(titles, fallback)` → LLM-generated 3-6 word label
- `_llm_coherence_check(titles)` → LLM coherence score 0.0-1.0
- `_tfidf_topic_label(...)` → TF-IDF average-based keyword label

**Dependencies**: numpy, spacy (en_core_web_sm), sklearn (MiniBatchKMeans, TfidfVectorizer, cosine_similarity)

---

### Summarization (`backend/app/services/summarization.py`)

Generates commit messages and details for clusters with new articles.

**Entry point**: `async def run_summarization(db: AsyncSession) -> int`

**Algorithm**:
1. Load active/cooling clusters with articles and commits
2. For each cluster: identify articles not yet covered by existing commits
3. If new articles exist: generate commit via `generate_commit(topic_label, articles)`
4. Create Commit row with message, detail, article_ids, commit_date

**Commit generation** (`generate_commit`):
- Tries LLM first via `_llm_commit(topic_label, articles)`
- Falls back to LexRank via `_lexrank_commit(articles)`

**LexRank path** (`_lexrank_commit`):
- Concatenates up to 10 most recent articles (title + cleaned summary)
- Uses Sumy LexRank with English tokenizer/stopwords
- Extracts 3-sentence summary → detail
- First 150 chars of first sentence → message

**Catch-up narrative** (`generate_catchup`):
- Builds readable narrative from commit list (first commit, developments, latest)

**Dependencies**: sumy (LexRank, Stemmer, Tokenizer), nltk

---

### Lifecycle (`backend/app/services/lifecycle.py`)

Updates cluster heat scores and transitions between states.

**Entry point**: `async def run_lifecycle(db: AsyncSession) -> dict[str, int]`

**Algorithm**:
1. Fetch all clusters with articles and commits
2. Recompute heat via `calculate_heat(articles, commits)`
3. Determine new state via `determine_state(heat, current_state, last_article_at)`
4. If state changed: update cluster, log transition

**State transitions** (`determine_state`):
- heat ≥ ACTIVE_THRESHOLD (3.0) → active
- heat ≥ COOLING_THRESHOLD (1.0) → cooling
- last_article_at > HIBERNATION_DAYS (3) ago → hibernated
- Already hibernated → stay hibernated
- Default → cooling

---

### Cleanup (`backend/app/services/cleanup.py`)

Prunes old articles and empty hibernated clusters.

**Entry point**: `async def cleanup_old_articles(db: AsyncSession)`

**Algorithm**:
1. Compute cutoff: now - `settings.article_retention_days` (default 30)
2. Delete articles older than cutoff where cluster is hibernated (batch size 500)
3. Delete hibernated clusters with zero remaining articles
4. On error: rollback and log

---

### GDELT Backfill (`backend/app/services/gdelt.py`)

Historical context from GDELT Doc API for clusters with few commits.

**Entry point**: `async def run_gdelt_backfill(db: AsyncSession) -> int`

**Algorithm**:
1. Find active/cooling clusters with < 4 commits
2. For each: build search query via LLM (fallback: keyword extraction)
3. Backfill 20 days of history in 5-day windows (4 windows per cluster)
4. For each window: fetch GDELT articles → deduplicate → create Article rows → generate commit summary
5. Create Commit rows anchored to window dates

**Key constants**: BACKFILL_DAYS=20, DAYS_PER_WINDOW=5, MAX_ARTICLES_PER_WINDOW=25

**GDELT quirks**: Returns HTML error pages for some queries (JSON parse failure); `sourcelang:english` filter unreliable (post-fetch filtering required); rate limited ~1 req/s; 429 → sleep 10s and retry

---

## API Reference

### GET /api/health

Returns system health status.

**Response** (`HealthResponse`):
```json
{
  "status": "ok",
  "last_ingestion": "2026-04-27T10:30:00Z",
  "active_stories": 12,
  "total_articles": 1543
}
```

Status is "ok" if articles exist; "degraded" otherwise.

---

### GET /api/stories

Lists all active/cooling story clusters, ordered by heat_score DESC.

**Rate limit**: 30/minute
**Caching**: 5-minute in-process cache (invalidated on ingest)

**Response**: `StoryCard[]`
```json
[{
  "id": "uuid",
  "topic_label": "US-China Trade Tensions",
  "topic_tokens": ["US-China", "Trade", "Tensions"],
  "latest_commit_message": "New tariffs announced...",
  "heat_score": 6.9,
  "state": "active",
  "article_count": 23,
  "last_updated": "2026-04-27T09:00:00Z"
}]
```

---

### GET /api/stories/{story_id}

Returns full story detail with commits and entity fingerprint.

**Response**: `StoryDetail`
```json
{
  "id": "uuid",
  "topic_label": "US-China Trade Tensions",
  "topic_tokens": ["US-China", "Trade", "Tensions"],
  "state": "active",
  "heat_score": 6.9,
  "article_count": 23,
  "entity_fingerprint": ["United States", "China", "TSMC"],
  "commits": [
    {
      "id": "uuid",
      "message": "New tariffs announced on semiconductor exports",
      "detail": "Full narrative summary...",
      "commit_date": "2026-04-27T09:00:00Z",
      "source_count": 5,
      "source_urls": ["https://..."]
    }
  ],
  "created_at": "2026-04-20T00:00:00Z",
  "updated_at": "2026-04-27T09:00:00Z"
}
```

---

### GET /api/stories/{story_id}/commits

Paginated commit history for a story.

**Query params**: `limit` (default 20), `offset` (default 0)
**Response**: `CommitResponse[]`

---

### GET /api/stories/{story_id}/catchup

Generates a narrative catch-up summary from all commits.

**Response**: `CatchUpResponse`
```json
{
  "story_id": "uuid",
  "narrative": "This story began when... Key developments include...",
  "commit_count": 8,
  "time_span_days": 7
}
```

---

### GET /api/search

Full-text article search using PostgreSQL tsvector.

**Query params**: `q` (required), `limit` (1-100, default 20), `offset` (≥0, default 0)
**Response**: `SearchResult[]`

Uses `plainto_tsquery('english', q)` and ranks by `ts_rank`.

---

### POST /api/ingest

Triggers manual feed ingestion.

**Query params**: `full_pipeline` (bool, default false)

When `full_pipeline=true`: runs ingest → clustering → summarization → lifecycle → GDELT backfill sequentially, then invalidates the stories cache.

---

## Scheduler & Orchestration

APScheduler runs three jobs in-process (AsyncIOScheduler in FastAPI lifespan):

| Job | Schedule | Pipeline |
|-----|----------|----------|
| ingest_feeds_job | Every 30 minutes | `ingest_feeds(session)` |
| clustering_job | Every 2 hours | `run_clustering` → `run_summarization` → `run_lifecycle` → `run_gdelt_backfill` → invalidate cache |
| cleanup_job | Daily at 03:00 UTC | `cleanup_old_articles(session)` |

Each job creates its own `AsyncSession` via `async_session_factory()` and wraps everything in try/except with `logger.exception()`.

The clustering job runs the full processing pipeline sequentially — clustering creates/updates clusters, summarization generates commits for new articles, lifecycle transitions states based on heat, and GDELT backfills history for under-documented clusters.

---

## LLM Integration

### Architecture (`backend/app/services/llm.py`)

Dual-provider system with prompt caching and graceful fallbacks.

**Providers**:
1. **DMR (Docker Model Runner)**: Local inference via Llama 3.2 1B (Q4_0 quantized). Base URL: `model-runner.docker.internal:12434`. Runs on host machine, not in container.
2. **Groq**: Cloud fallback. Requires `GROQ_API_KEY` env var.
3. **Embedding**: Qwen3 0.6B (F16) via DMR for dense vector embeddings.

**Provider selection**: Configured via `settings.llm_provider` ("groq" or "dmr"). Primary provider tried first; other used as fallback.

**Prompt cache**: In-memory dict with 600s TTL. SHA-256 hash of system+user prompt as key. Avoids redundant API calls during pipeline runs.

**Functions**:

| Function | Purpose | Fallback |
|----------|---------|----------|
| `_call_llm(system, user, json_mode, max_tokens)` | Core LLM call with multi-provider retry | Returns None if all fail |
| `generate_topic_label(titles)` | 3-6 word topic label | Regex extraction, string slice |
| `score_coherence(titles)` | 0.0-1.0 cluster coherence score | Returns 0.0 |
| `generate_commit_summary(topic, titles, summaries)` | (message, detail) commit tuple | Returns None → triggers LexRank |
| `get_embeddings(texts)` | Dense vector array (numpy) | Returns None → triggers TF-IDF |

**Llama 3.2 1B quirks**: Sometimes parrots prompt examples or outputs malformed JSON. `llm.py` has regex fallback parsing and rejects template values.

---

## Frontend Architecture

### Stack

Next.js 14.2.35 App Router, React 18, Tailwind 3.4, shadcn/ui, @base-ui/react, next-themes, class-variance-authority.

### Pages (Server Components)

| Route | File | Rendering | Data Fetching |
|-------|------|-----------|---------------|
| `/` | `src/app/page.tsx` | SSR (force-dynamic, revalidate 300) | `fetchStories()` |
| `/story/[id]` | `src/app/story/[id]/page.tsx` | SSR (revalidate 60) | `fetchStory(id)` + `fetchStories()` |
| `/search` | `src/app/search/page.tsx` | SSR (force-dynamic) | `searchArticles(q)` |

All pages are server components. Data fetched server-side via `SERVER_API_BASE` (Docker: `http://backend:8000`).

### Layout (`src/app/layout.tsx`)

Root layout wraps all routes:
- Fonts: Newsreader (serif, `--font-serif`) + Inter (sans, `--font-sans`) via `next/font/google`
- Material Symbols Outlined via `<link>` in `<head>`
- `<ThemeProvider>` from next-themes (attribute="class", defaultTheme="light")
- Structure: `TopNav` → flex container with `Sidebar` + content area (`main` + `Footer`)

### Components

**Shell (3)**:
| Component | Type | Purpose |
|-----------|------|---------|
| `top-nav.tsx` | Client | Fixed header: brand, nav links (Home Feed, Search), SearchBar, Ingest Refresh (wired to POST /api/ingest), ThemeToggle |
| `sidebar.tsx` | Client | Left rail (w-64): Intelligence Hub header, nav items with MaterialIcons, mobile overlay |
| `footer.tsx` | Server | Brand, copyright |

**Dashboard (5)**:
| Component | Type | Purpose |
|-----------|------|---------|
| `featured-card.tsx` | Client | Hero card: category pill, LIVE badge, headline, description, hover lift, dark mode glow |
| `story-card.tsx` | Client | Standard card: HeatBadge, headline, description, sources, relative time |
| `live-badge.tsx` | Server | Animated dot + "LIVE" text |
| `morning-digest.tsx` | Client | Top 5 stories by heat, bulleted links |
| `sidebar-timeline.tsx` | Client | Vertical timeline, orange/gray dots, topic + latest commit |

**Story Detail (5)**:
| Component | Type | Purpose |
|-----------|------|---------|
| `executive-synthesis.tsx` | Client | Replaces CatchUpPanel: orange accent bar, Generate button, bullet narrative, loading state |
| `entity-chips.tsx` | Server | KEY ENTITIES sidebar: grid of chips from entity_fingerprint |
| `sparkline.tsx` | Server | 72hr Velocity SVG: 12×6hr windows, polyline chart |
| `commit-log.tsx` | Client | Editorial timeline: orange/gray dots, timestamps, expandable sources |
| `related-clusters.tsx` | Server | 2-col grid of related story cards |

**Search (3)**:
| Component | Type | Purpose |
|-----------|------|---------|
| `search-bar.tsx` | Client | GET form to /search, inline search icon |
| `search-result-card.tsx` | Server | Left accent border, source/date, AI badge, query highlighting |
| `empty-state.tsx` | Server | Dashed border, icon, title, description, actions |

**Shared (5)**:
| Component | Type | Purpose |
|-----------|------|---------|
| `heat-badge.tsx` | Server | HIGH HEAT / RISING HEAT / COOLING with numeric score |
| `material-icon.tsx` | Server | Material Symbols Outlined icon wrapper |
| `theme-toggle.tsx` | Client | Light/dark toggle via next-themes |
| `story-card-skeleton.tsx` | Client | Loading skeleton for story cards |
| `story-detail-skeleton.tsx` | Client | Loading skeleton for story detail |

**UI Primitives (6)**: badge, button, card, separator, skeleton, scroll-area (from shadcn/ui + @base-ui/react)

### Data Flow (`src/lib/api.ts`)

```
Browser → Next.js Server Component → fetch(SERVER_API_BASE/api/...) → FastAPI → PostgreSQL
                                      ↓
                                   JSON response
                                      ↓
                              Rendered as HTML (SSR)
                                      ↓
                              Hydrated on client
```

**URL resolution**:
- `API_BASE` = `NEXT_PUBLIC_API_URL` (client-side, browser: `http://localhost:8000`)
- `SERVER_API_BASE` = `API_URL` (server-side, Docker: `http://backend:8000`) || `API_BASE`

Server components use `SERVER_API_BASE` (internal Docker network). Client components (like Ingest Refresh) use `NEXT_PUBLIC_API_URL` (browser-accessible).

---

## Design System

### Typography

Dual-font editorial system:
- **Newsreader** (serif): Display headlines, story titles, brand
- **Inter** (sans): Body text, UI elements, metadata

| Token | Size | Weight | Font | Usage |
|-------|------|--------|------|-------|
| display-xl | 64px | 600 | Newsreader | Story detail hero |
| headline-lg | 40px | 500 | Newsreader | Page titles |
| headline-md | 24px | 600 | Newsreader | Section headers, card titles |
| body-lg | 18px | 400 | Inter | Primary body text |
| body-md | 16px | 400 | Inter | Standard body |
| body-sm | 14px | 400 | Inter | Secondary text |
| label-caps | 13px | 600 | Inter | 0.05em tracking, uppercase labels |
| label-caps-sm | 11px | 600 | Inter | 0.05em tracking, small labels |
| metadata | 12px | 500 | Inter | Timestamps, counts |

### Color Palette

**Light Mode** (Editorial Intelligence):
| Token | Value | Usage |
|-------|-------|-------|
| --background | #f9f9f8 | Page background |
| --foreground | #191c1c | Primary text |
| --primary | #000000 | Headlines, strong elements |
| --secondary | #a93100 | International Orange — accents, LIVE badges, accent bars |
| --surface-container | #f0f0ee | Card backgrounds, chips |
| --surface-container-lowest | #ffffff | Elevated surfaces |
| --muted-foreground | #76777d | Secondary text, metadata |
| --outline | #c4c6cf | Borders |

**Dark Mode** (Intelligence Navy):
| Token | Value | Usage |
|-------|-------|-------|
| --background | #0f172a | Deep navy page background |
| --foreground | #f8fafc | Primary text |
| --primary | #ea580c | Vibrant orange — headlines, accents |
| --secondary | #ea580c | Same as primary in dark |
| --surface-container | #1e293b | Card backgrounds |
| --surface-container-lowest | #1e293b | Elevated surfaces |
| --muted-foreground | #94a3b8 | Secondary text |
| --outline | #334155 | Borders |

### Spacing

4px base unit:
| Token | Value |
|-------|-------|
| --space-xs | 4px |
| --space-sm | 8px |
| --space-md | 16px |
| --space-lg | 24px |
| --space-xl | 48px |
| --space-2xl | 64px |
| --layout-gutter | 24px |
| --layout-margin | 64px |
| --container-max | 1280px |

### Elevation

| Token | Value | Usage |
|-------|-------|-------|
| whisper-shadow | 0 2px 8px rgba(0,0,0,0.04) | Default card shadow |
| hover-shadow | 0 10px 20px rgba(0,0,0,0.08) | Card hover state |
| ambient-shadow | 0 10px 30px rgba(0,0,0,0.12) | Prominent elements |
| glow-border | 1px solid rgba(255,255,255,0.1) | Dark mode card borders |

### Border Radius

| Token | Value |
|-------|-------|
| --radius-sm | 2px |
| --radius | 4px |
| --radius-md | 6px |
| --radius-lg | 8px |
| --radius-full | 9999px |

### Icons

Material Symbols Outlined loaded via Google Fonts CDN. Rendered through `<MaterialIcon name="..." size={24} />` component. Settings: FILL 0, wght 300, GRAD 0, opsz 24.

---

## Configuration & Environment

### Backend Settings (`backend/app/config.py`)

Pydantic BaseSettings with `.env` file support:

| Setting | Default | Env Var | Notes |
|---------|---------|---------|-------|
| database_url | postgresql+asyncpg://chronicle:chronicle_dev@localhost:5432/chronicle | DATABASE_URL | Async PostgreSQL connection |
| frontend_url | http://localhost:3000 | FRONTEND_URL | CORS allowed origin |
| ingestion_interval_minutes | 30 | INGESTION_INTERVAL_MINUTES | RSS poll frequency |
| clustering_interval_hours | 2 | CLUSTERING_INTERVAL_HOURS | Full pipeline frequency |
| article_retention_days | 30 | ARTICLE_RETENTION_DAYS | Cleanup cutoff |
| groq_api_key | "" | GROQ_API_KEY | Cloud LLM fallback |
| llm_provider | "groq" | LLM_PROVIDER | Primary: "groq" or "dmr" |
| llm_model | ai/llama3.2:1B-Q4_0 | LLM_MODEL | DMR model identifier |
| llm_base_url | http://model-runner.docker.internal:12434/engines/v1 | LLM_BASE_URL | DMR endpoint |
| embedding_model | ai/qwen3-embedding:0.6B-F16 | EMBEDDING_MODEL | Embedding model |
| embedding_base_url | http://model-runner.docker.internal:12434/engines/llama.cpp/v1 | EMBEDDING_BASE_URL | Embedding endpoint |

### Frontend Environment

| Variable | Server/Client | Docker Default | Purpose |
|----------|--------------|----------------|---------|
| NEXT_PUBLIC_API_URL | Client (browser) | http://localhost:8000 | Browser-accessible API base |
| API_URL | Server only | http://backend:8000 | SSR fetch base (Docker DNS) |

### Core Utilities

- **Database** (`core/database.py`): Async SQLAlchemy engine (pool_size=5, max_overflow=10), `async_session_factory` (expire_on_commit=False), `get_db()` dependency generator
- **Logging** (`core/logging.py`): Single `chronicle` logger, StreamHandler to stdout, timestamped format
- **Rate Limiting** (`core/limiter.py`): SlowAPI Limiter with `get_remote_address` key function

---

## Docker & Deployment

### docker-compose.yml

Three services on a shared Docker network:

```
postgres (5432)  ←──  backend (8000)  ←──  frontend (3000)
                            ↕
                   model-runner (host:12434)
```

| Service | Image/Build | Ports | Key Config |
|---------|-------------|-------|------------|
| postgres | postgres:16-alpine | 5432 | DB: chronicle, User: chronicle, healthcheck |
| backend | ./backend | 8000 | DATABASE_URL → postgres:5432, env_file ./backend/.env, extra_hosts for DMR |
| frontend | ./frontend | 3000 | NEXT_PUBLIC_API_URL=localhost:8000, API_URL=backend:8000 |

**DMR networking**: `extra_hosts: model-runner.docker.internal:host-gateway` maps the DMR hostname to the Docker host, where the model runner process listens on port 12434.

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm
RUN python -c "import nltk; nltk.download('punkt_tab')"
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

Multi-stage build: deps → builder → runner. Standalone Next.js output. Node 20 Alpine.

### Deployment Configs

- `backend/railway.toml`: Railway deployment config
- `frontend/vercel.json`: Vercel deployment config

---

## Database Migrations

### 001_initial_schema

Creates the complete database schema:

**Tables**: clusters, articles, commits (all with UUID primary keys via `gen_random_uuid()`)

**Indexes (7)**:
- `idx_articles_published` — articles(published_at DESC)
- `idx_articles_cluster` — articles(cluster_id)
- `idx_articles_search` — articles(search_vector) GIN
- `idx_commits_cluster` — commits(cluster_id)
- `idx_commits_date` — commits(commit_date DESC)
- `idx_clusters_heat` — clusters(heat_score DESC)
- `idx_clusters_state` — clusters(state)

**Full-text search trigger**:
```sql
CREATE FUNCTION articles_search_trigger() RETURNS trigger
  -- Updates search_vector = to_tsvector('english', title || ' ' || coalesce(summary, ''))
CREATE TRIGGER trg_articles_search BEFORE INSERT OR UPDATE ON articles
  FOR EACH ROW EXECUTE FUNCTION articles_search_trigger()
```

**Note**: `alembic.ini` has localhost URL; `env.py` overrides with `settings.database_url` at runtime. Set `DATABASE_URL` env var for migrations outside Docker.

---

## Dependencies

### Backend (requirements.txt)

| Category | Packages |
|----------|----------|
| Web framework | fastapi ≥0.110, uvicorn[standard] ≥0.27 |
| Database | sqlalchemy[asyncio] ≥2.0, asyncpg ≥0.29, alembic ≥1.13 |
| Scheduling | apscheduler ≥3.10 |
| RSS | feedparser ≥6.0 |
| NLP | spacy ≥3.7, sumy ≥0.11, nltk ≥3.8 |
| Clustering | scikit-learn ≥1.4, numpy ≥1.26 |
| Rate limiting | slowapi ≥0.1.9 |
| LLM | openai ≥1.12 |
| HTTP | httpx ≥0.27 |
| Config | python-dotenv ≥1.0, pydantic ≥2.6, pydantic-settings ≥2.1 |

**Build-time downloads**: spaCy `en_core_web_sm` model, NLTK `punkt_tab` tokenizer

### Frontend (package.json)

| Category | Packages |
|----------|----------|
| Framework | next 14.2.35, react 18, react-dom 18 |
| UI | @base-ui/react, class-variance-authority, clsx, tailwind-merge |
| Styling | tailwindcss 3.4.1, tw-animate-css |
| Components | shadcn 4.5.0 |
| Theming | next-themes |
| Dev | typescript 5, @types/react, eslint, postcss, autoprefixer |

---

## Data Flow Diagrams

### Full Pipeline Flow

```
RSS Feeds (BBC, Reuters, The Hindu, NDTV, NPR, Al Jazeera)
    │
    ▼
┌──────────────┐
│  Ingestion   │ → Creates Article rows (cluster_id = NULL)
│  (30min)     │
└──────┬───────┘
       │ unclustered articles
       ▼
┌──────────────┐     ┌──────────────┐
│  Clustering  │ ──→ │  LLM Service │ (embeddings, coherence, labels)
│  (2hr)       │ ←── │              │
└──────┬───────┘     └──────────────┘
       │ clusters with assigned articles
       ▼
┌──────────────┐     ┌──────────────┐
│Summarization │ ──→ │  LLM Service │ (commit summaries)
│              │ ←── │              │ fallback: LexRank
└──────┬───────┘     └──────────────┘
       │ commits created
       ▼
┌──────────────┐
│  Lifecycle   │ → Updates heat_score, transitions state
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│    GDELT     │ ──→ │  LLM Service │ (search queries, summaries)
│  Backfill    │ ←── │              │
└──────┬───────┘     └──────────────┘
       │ historical commits
       ▼
   Cache invalidated → Frontend sees updated data
```

### Cleanup Flow (Daily 03:00 UTC)

```
┌──────────────┐
│   Cleanup    │
└──────┬───────┘
       │
       ├─→ Delete articles older than 30 days in hibernated clusters (batch 500)
       │
       └─→ Delete hibernated clusters with 0 articles
```

### Frontend Data Flow

```
User visits page
       │
       ▼
Next.js Server Component
       │
       ├─→ fetch(SERVER_API_BASE/api/stories)     [Docker: http://backend:8000]
       ├─→ fetch(SERVER_API_BASE/api/stories/{id}) [Docker: http://backend:8000]
       └─→ fetch(SERVER_API_BASE/api/search?q=)    [Docker: http://backend:8000]
       │
       ▼
SSR HTML response → Browser hydrates client components
       │
       ├─→ Ingest Refresh: fetch(NEXT_PUBLIC_API_URL/api/ingest) [Browser: http://localhost:8000]
       └─→ Executive Synthesis: fetch(NEXT_PUBLIC_API_URL/api/stories/{id}/catchup)
```

---

## Key Constants & Thresholds

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| MIN_ARTICLES_TO_CLUSTER | 3 | clustering.py | Minimum articles to form a new cluster |
| MAX_CLUSTERS | 25 | clustering.py | Maximum clusters per KMeans run |
| SIMILARITY_THRESHOLD | 0.55 | clustering.py | Minimum combined score to assign to existing cluster |
| DECAY_LAMBDA | 0.15 | clustering.py | Exponential decay rate for heat calculation |
| COHERENCE_THRESHOLD | 0.4 | clustering.py | LLM coherence gate for new clusters |
| ACTIVE_THRESHOLD | 3.0 | lifecycle.py | Heat score above which cluster is "active" |
| COOLING_THRESHOLD | 1.0 | lifecycle.py | Heat score above which cluster is "cooling" |
| HIBERNATION_DAYS | 3 | lifecycle.py | Days without articles before hibernation |
| BATCH_SIZE | 500 | cleanup.py | Cleanup deletion batch size |
| CACHE_TTL | 600 | llm.py | LLM prompt cache expiry (seconds) |
| BACKFILL_DAYS | 20 | gdelt.py | GDELT historical window |
| DAYS_PER_WINDOW | 5 | gdelt.py | GDELT window granularity |
| MAX_ARTICLES_PER_WINDOW | 25 | gdelt.py | GDELT articles per fetch |
| Stories cache TTL | 300 | stories.py | API response cache (seconds) |

---

## Error Handling Patterns

1. **Scheduler jobs**: Every job (ingest, cluster, cleanup) wrapped in try/except with `logger.exception()`. Jobs never crash the process.

2. **Per-feed ingestion**: Each RSS feed commits independently. Failure in one feed → rollback that feed, continue with others.

3. **LLM fallbacks**: Every LLM call has a non-LLM fallback:
   - Embeddings fail → TF-IDF vectorization
   - Topic label fails → TF-IDF keyword extraction
   - Coherence check fails → score 0.0 (skip cluster)
   - Commit summary fails → LexRank extractive summary

4. **LLM multi-provider**: Primary provider fails → try secondary. Both fail → return None.

5. **GDELT resilience**: HTTP 429 → sleep 10s, retry. Other errors → log, return empty, continue.

6. **API endpoints**: DB errors caught and return graceful degraded responses. Global exception handler returns 500 with structured JSON.

7. **Frontend SSR**: All page data fetches wrapped in try/catch. On error → show empty state, not crash.

---

## Anti-Patterns

Things explicitly avoided in this codebase:

- `as any`, `@ts-ignore`, `@ts-expect-error` — never in TypeScript
- `print()` for logging — always use `logger` from `app.core.logging`
- Relative imports — absolute only (`from app.core.logging import logger`)
- Direct `engine.execute()` — always use `AsyncSession` via `get_db` or `async_session_factory`
- Raw SQL strings for JSONB defaults in Alembic — wrap with `sa.text()`
- Comments in code — codebase is comment-free by design
- N+1 queries — use subqueries or joinedload/selectinload
- Hardcoded hex colors in frontend — always CSS variables via Tailwind tokens

---

## Gotchas

1. **Alembic URL**: `alembic.ini` has localhost URL; `env.py` overrides with `settings.database_url`. Set `DATABASE_URL` env var for migrations outside Docker.

2. **No .env in repo**: Only `.env.example`. Docker Compose passes env vars directly. Local dev needs `.env` from `.env.example`.

3. **Partial ingestion**: Each RSS feed commits independently — partial ingestion on failure is by design.

4. **Dockerfile runs as root**: No USER instruction. Acceptable for dev, needs hardening for prod.

5. **spaCy model baked into image**: Changing model requires full image rebuild.

6. **In-process scheduler**: APScheduler runs inside FastAPI. No external job queue.

7. **Docker network routing**: Server-side Next.js uses `API_URL=http://backend:8000`. Client-side uses `NEXT_PUBLIC_API_URL=http://localhost:8000`.

8. **NLTK punkt_tab**: Downloaded at build time. If missing, LexRank summarization fails silently.

9. **DMR cold start**: First request loads model into memory (5-15s). Rapid requests during cold start cause LLM fallback to LexRank/TF-IDF.

10. **Llama 3.2 1B JSON compliance**: Sometimes parrots prompt examples or outputs malformed JSON. `llm.py` has regex fallback parsing.

11. **GDELT quirks**: Returns HTML error pages for some queries; `sourcelang:english` unreliable; rate limited ~1 req/s.

12. **entity_fingerprint optional**: Frontend treats `entity_fingerprint` as optional (`string[] | undefined`) because older backend builds may not return it.

---

## Commands

```bash
docker compose up --build                    # Start everything
docker compose up -d --build                 # Start detached
docker compose exec backend alembic upgrade head  # Run migrations
curl http://localhost:8000/api/health        # Health check
curl -X POST "http://localhost:8000/api/ingest?full_pipeline=true"  # Full pipeline
docker compose down -v && docker compose up --build  # Rebuild from scratch
docker compose logs -f backend               # Backend logs
docker compose exec postgres psql -U chronicle -d chronicle_db  # DB shell
```
