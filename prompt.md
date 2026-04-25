# Chronicle AI — MVP Implementation Prompt

## Project Overview

**Chronicle AI** is a free, consumer-facing web application that ingests news via RSS feeds, clusters articles into story timelines, and presents them as clean chronological "commit logs" — one per topic. Each development is a "commit" with a one-line summary, timestamp, and expandable three-sentence detail.

**Target User**: Working-class adults (nurses, drivers, retail workers) with 3–5 minutes during lunch breaks to stay informed without following news daily.

**Core Constraints**:
- No accounts, no infinite scroll, no algorithmic manipulation
- Zero deployment cost (free-tier only)
- Single developer (undergrad), 8-week timeline
- ≤512 MB RAM on backend (Railway free tier)

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      CHRONICLE AI (MVP)                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  BBC World   │  │  Reuters     │  │  AP News     │         │
│  │  (RSS)       │  │  (RSS)       │  │  (RSS)       │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         └──────────────────┼─────────────────┘                 │
│                            ▼                                   │
│           ┌────────────────────────────────┐                   │
│           │      INGESTION SERVICE         │                   │
│           │  (APScheduler — every 30 min)  │                   │
│           │  - feedparser                  │                   │
│           │  - Dedup by URL hash           │                   │
│           └────────────────┬───────────────┘                   │
│                            ▼                                   │
│           ┌────────────────────────────────┐                   │
│           │     CLUSTERING SERVICE         │                   │
│           │  (APScheduler — every 2 hrs)   │                   │
│           │  1. TF-IDF vectorization       │                   │
│           │  2. KMeans clustering          │                   │
│           │  3. spaCy NER (en_core_web_sm) │                   │
│           │  4. Heat score calculation      │                   │
│           └────────────────┬───────────────┘                   │
│                            ▼                                   │
│           ┌────────────────────────────────┐                   │
│           │    SUMMARIZATION SERVICE       │                   │
│           │  (Triggered on cluster update) │                   │
│           │  - LexRank extractive summary  │                   │
│           │  - Keyword-based topic labels  │                   │
│           └────────────────┬───────────────┘                   │
│                            ▼                                   │
│           ┌────────────────────────────────┐                   │
│           │         PostgreSQL             │                   │
│           │  (Standard — no pgvector)      │                   │
│           │  + Full-text search (tsvector) │                   │
│           └────────────────┬───────────────┘                   │
│                            ▼                                   │
│           ┌────────────────────────────────┐                   │
│           │       FASTAPI SERVER           │                   │
│           │  (Single process w/ scheduler) │                   │
│           │  /stories, /commits, /catchup  │                   │
│           └────────────────┬───────────────┘                   │
│                            ▼                                   │
│           ┌────────────────────────────────┐                   │
│           │      NEXT.JS 14 FRONTEND       │                   │
│           │  - Dashboard (topic cards)     │                   │
│           │  - Story log (commit view)     │                   │
│           │  - Catch Me Up (extractive)    │                   │
│           └────────────────────────────────┘                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Key simplifications vs. the original design:**
- **No Celery/Redis** — APScheduler runs in-process within FastAPI. At <500 users, a separate task queue is unnecessary operational complexity.
- **No pgvector/embeddings** — TF-IDF + KMeans replaces SBERT + HDBSCAN. Fits in <50 MB RAM vs. 600 MB+ for transformer models.
- **No Ollama/LLM** — Extractive summarization (LexRank) + templates replace Mistral 7B. Zero GPU/8GB RAM requirement.
- **No GDELT/NewsAPI** — RSS-only for MVP. GDELT adds a client library, GKG parsing, and rate-limit management for marginal gain. Add post-MVP.
- **No BERTopic** — Simple TF-IDF keyword extraction for topic labels. BERTopic re-fits on every call — expensive and unnecessary.
- **Single backend** — FastAPI is the sole backend. Next.js handles rendering only (no API routes). One data path, no confusion.

---

## Database Schema

### PostgreSQL Tables

```sql
-- Articles table
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url VARCHAR(2048) UNIQUE NOT NULL,
    url_hash VARCHAR(64) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,                          -- RSS summary/description field
    source VARCHAR(255) NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    entities JSONB DEFAULT '[]'::jsonb,    -- spaCy NER extracted entities
    cluster_id UUID REFERENCES clusters(id),
    search_vector tsvector,               -- Full-text search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Story clusters table
CREATE TABLE clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_label VARCHAR(500) NOT NULL,     -- TF-IDF keyword-based label
    state VARCHAR(20) DEFAULT 'active'
        CHECK (state IN ('active', 'cooling', 'hibernated')),
    heat_score FLOAT DEFAULT 0.0,
    entity_fingerprint JSONB DEFAULT '[]'::jsonb,  -- Aggregated NER entities
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_article_at TIMESTAMP WITH TIME ZONE
);

-- Commits table (one per story development)
CREATE TABLE commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    message VARCHAR(150) NOT NULL,         -- One-line LexRank summary
    detail TEXT NOT NULL,                  -- Three-sentence expansion
    article_ids UUID[] NOT NULL,           -- Source articles for this commit
    commit_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_articles_published ON articles(published_at DESC);
CREATE INDEX idx_articles_cluster ON articles(cluster_id);
CREATE INDEX idx_articles_search ON articles USING GIN(search_vector);
CREATE INDEX idx_commits_cluster ON commits(cluster_id);
CREATE INDEX idx_commits_date ON commits(commit_date DESC);
CREATE INDEX idx_clusters_heat ON clusters(heat_score DESC);
CREATE INDEX idx_clusters_state ON clusters(state);

-- Auto-update search vector on insert/update
CREATE OR REPLACE FUNCTION articles_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.summary, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_articles_search
    BEFORE INSERT OR UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION articles_search_trigger();
```

**What was removed:**
- `users` and `user_follows` tables — contradicted the "no accounts" constraint. Follow/notify is a post-MVP feature that requires authentication.
- `embedding vector(384)` column — no embeddings in MVP; TF-IDF is computed in-memory at clustering time.
- `sentiment JSONB` columns — VADER sentiment is not user-facing in MVP. Add when there's a UI for it.
- `gkg_codes`, `location` columns — GDELT-specific fields; no GDELT in MVP.
- `parent_cluster_id` (branching) — story branching is a post-MVP feature.

**What was added:**
- `search_vector tsvector` + GIN index — enables fast full-text search without pgvector.
- `CHECK` constraint on `clusters.state` — enforces valid states at the DB level.
- `ON DELETE CASCADE` on commits → clusters — prevents orphaned commits.
- Trigger for auto-updating search vectors.

---

## Core Components Specification

### 1. Data Ingestion Service

**Objective**: Fetch articles from RSS feeds every 30 minutes.

#### RSS Feed Sources

| Source | URL | Priority |
|--------|-----|----------|
| BBC World | `http://feeds.bbci.co.uk/news/world/rss.xml` | 1 |
| Reuters World | `https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best` | 1 |
| AP News | `https://feeds.apnews.com/apnews/topnews` | 1 |
| The Hindu | `https://www.thehindu.com/news/feeds/default/rssfeed.xml` | 2 |
| NDTV | `https://feeds.ndtv.com/ndrss/news` | 2 |

#### Implementation

```python
import feedparser
import hashlib
from apscheduler.schedulers.asyncio import AsyncIOScheduler

RSS_FEEDS = [
    {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Reuters", "url": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best"},
    {"name": "AP News", "url": "https://feeds.apnews.com/apnews/topnews"},
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/feeds/default/rssfeed.xml"},
    {"name": "NDTV", "url": "https://feeds.ndtv.com/ndrss/news"},
]

def normalize_url(url: str) -> str:
    """Strip query params and trailing slash, lowercase."""
    return url.split('?')[0].rstrip('/').lower()

def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()

async def ingest_feeds(db: AsyncSession):
    """Fetch all RSS feeds and insert new articles."""
    for feed_config in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_config["url"])
            for entry in feed.entries:
                h = url_hash(entry.link)
                exists = await db.execute(
                    select(Article).where(Article.url_hash == h)
                )
                if exists.scalar_one_or_none():
                    continue

                article = Article(
                    url=entry.link,
                    url_hash=h,
                    title=entry.get("title", "Untitled"),
                    summary=entry.get("summary", ""),
                    source=feed_config["name"],
                    published_at=parse_published_date(entry),
                )
                db.add(article)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to ingest {feed_config['name']}: {e}")
            await db.rollback()
```

#### Scheduling (APScheduler — in-process)

```python
# In FastAPI lifespan
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(ingest_feeds_job, "interval", minutes=30, id="ingest")
    scheduler.add_job(run_clustering_job, "interval", hours=2, id="cluster")
    scheduler.add_job(cleanup_old_articles_job, "cron", hour=3, id="cleanup")
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

**Why APScheduler over Celery+Redis**: One fewer service to deploy, configure, and monitor. At <500 users with 5 RSS feeds, the workload is trivial — a single async loop handles it. Celery becomes justified when you need distributed workers or >1 process.

### 2. Clustering Service

**Objective**: Group related articles into story clusters using lightweight NLP.

#### TF-IDF + KMeans Pipeline

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Configuration
MIN_ARTICLES_TO_CLUSTER = 3       # Minimum articles to form a cluster (relaxed from 5)
MAX_CLUSTERS = 25                  # Cap on active clusters
SIMILARITY_THRESHOLD = 0.3        # Minimum cosine sim to assign to existing cluster

def cluster_articles(unclustered_articles: list[Article], existing_clusters: list[Cluster]):
    """
    Two-pass clustering:
    1. Try to assign each article to an existing cluster (cosine sim on TF-IDF)
    2. Cluster remaining articles into new groups via KMeans
    """
    if not unclustered_articles:
        return

    # === Pass 1: Match against existing clusters ===
    if existing_clusters:
        # Build TF-IDF from existing cluster articles + unclustered
        all_texts = []
        cluster_text_map = {}

        for cluster in existing_clusters:
            cluster_texts = [f"{a.title} {a.summary}" for a in cluster.articles[-20:]]
            combined = " ".join(cluster_texts)
            cluster_text_map[cluster.id] = len(all_texts)
            all_texts.append(combined)

        unmatched = []
        for article in unclustered_articles:
            article_text = f"{article.title} {article.summary}"
            all_texts_with_article = all_texts + [article_text]

            vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            tfidf_matrix = vectorizer.fit_transform(all_texts_with_article)

            article_vec = tfidf_matrix[-1]
            cluster_vecs = tfidf_matrix[:-1]

            sims = cosine_similarity(article_vec, cluster_vecs).flatten()
            best_idx = np.argmax(sims)

            if sims[best_idx] >= SIMILARITY_THRESHOLD:
                best_cluster_id = list(cluster_text_map.keys())[best_idx]
                article.cluster_id = best_cluster_id
            else:
                unmatched.append(article)
    else:
        unmatched = unclustered_articles

    # === Pass 2: Cluster unmatched into new groups ===
    if len(unmatched) >= MIN_ARTICLES_TO_CLUSTER:
        texts = [f"{a.title} {a.summary}" for a in unmatched]
        vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
        tfidf = vectorizer.fit_transform(texts)

        n_clusters = min(len(unmatched) // MIN_ARTICLES_TO_CLUSTER, MAX_CLUSTERS)
        n_clusters = max(n_clusters, 1)

        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=100)
        labels = kmeans.fit_predict(tfidf)

        # Create new clusters from groups
        for label in set(labels):
            group = [unmatched[i] for i, l in enumerate(labels) if l == label]
            if len(group) >= MIN_ARTICLES_TO_CLUSTER:
                topic_label = extract_topic_label(group, vectorizer, tfidf, labels, label)
                new_cluster = Cluster(topic_label=topic_label)
                for article in group:
                    article.cluster_id = new_cluster.id
```

**Why TF-IDF + KMeans over SBERT + HDBSCAN:**
- **Memory**: TF-IDF is computed on-the-fly, no model to load. SBERT (`all-MiniLM-L6-v2`) needs ~100 MB resident.
- **Cold start**: KMeans works with `min_cluster_size=3` (relaxed from HDBSCAN's 5). On day 1 with limited articles, clusters form faster.
- **Simplicity**: scikit-learn is a standard dependency with no GPU requirements.
- **Trade-off**: Lower semantic quality — TF-IDF is bag-of-words, misses paraphrases. Acceptable for MVP with news headlines (high term overlap naturally).

#### Topic Label Extraction

```python
def extract_topic_label(articles: list[Article], vectorizer, tfidf_matrix, labels, target_label) -> str:
    """Extract top TF-IDF keywords as a topic label."""
    cluster_indices = [i for i, l in enumerate(labels) if l == target_label]
    cluster_tfidf = tfidf_matrix[cluster_indices].mean(axis=0).A1

    feature_names = vectorizer.get_feature_names_out()
    top_indices = cluster_tfidf.argsort()[-4:][::-1]
    keywords = [feature_names[i] for i in top_indices]

    return " — ".join(keywords).title()
```

#### NER for Cross-Temporal Linking

```python
import spacy

nlp = spacy.load('en_core_web_sm')  # ~15 MB, not 500 MB like en_core_web_trf

def extract_entities(text: str) -> list[str]:
    """Extract named entities for entity fingerprinting."""
    doc = nlp(text[:1000])  # Cap input length for performance
    return list(set(
        ent.text.lower()
        for ent in doc.ents
        if ent.label_ in ('PERSON', 'ORG', 'GPE', 'EVENT')
    ))

def entity_overlap_score(article_entities: list[str], cluster_entities: list[str]) -> float:
    """Jaccard similarity between entity sets."""
    if not article_entities or not cluster_entities:
        return 0.0
    a, c = set(article_entities), set(cluster_entities)
    return len(a & c) / len(a | c)
```

**Why `en_core_web_sm` over `en_core_web_trf`:** The transformer model is ~500 MB and won't fit alongside the app in 512 MB RAM. The small model is ~15 MB with slightly lower NER accuracy — acceptable for entity fingerprinting where we need "Israel", "Hamas", "Gaza" (proper nouns that even the small model handles well).

### 3. Story Lifecycle Management

#### Heat Score

```python
import math
from datetime import datetime, timezone

DECAY_LAMBDA = 0.15  # Faster decay than original (0.1) — news cycles are short

def calculate_heat(articles: list[Article]) -> float:
    """H(t) = Σ e^(-λ × Δt) where Δt is days since publication."""
    now = datetime.now(timezone.utc)
    score = 0.0
    for article in articles:
        delta_days = (now - article.published_at).total_seconds() / 86400
        score += math.exp(-DECAY_LAMBDA * delta_days)
    return round(score, 2)
```

#### State Machine (Simplified)

```
   ┌──────────┐  H < 3.0   ┌──────────┐  H < 1.0   ┌─────────────┐
   │  ACTIVE  │────────────>│ COOLING  │────────────>│ HIBERNATED  │
   └──────────┘             └──────────┘             └─────────────┘
        ▲                        ▲                         │
        │  New article matches   │                         │
        │  entity fingerprint    │                         │
        └────────────────────────┴─────────────────────────┘
```

| State | Condition | Dashboard Visibility |
|-------|-----------|---------------------|
| `active` | Heat ≥ 3.0 | Shown, sorted by heat |
| `cooling` | 1.0 ≤ Heat < 3.0 | Shown with "slowing down" badge |
| `hibernated` | Heat < 1.0 for 3+ days | Hidden from dashboard |

**Simplifications:**
- Removed "branched" state — story branching is complex and post-MVP.
- Removed source authority multiplier — over-engineering for 5 RSS sources with similar credibility.
- Lowered hibernation wait from 7 days to 3 — faster cleanup for an MVP with limited storage.

### 4. Summarization Service

#### LexRank for Commit Messages

```python
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

def generate_commit(articles: list[Article]) -> tuple[str, str]:
    """
    Generate:
    - message: One-line summary (≤150 chars)
    - detail: Three-sentence expansion
    """
    combined = "\n\n".join(
        f"{a.title}. {a.summary or ''}"
        for a in articles[-10:]  # Last 10 articles for recency
    )

    parser = PlaintextParser.from_string(combined, Tokenizer("english"))
    summarizer = LexRankSummarizer(Stemmer("english"))
    summarizer.stop_words = get_stop_words("english")

    sentences = summarizer(parser.document, 3)
    detail = " ".join(str(s) for s in sentences)
    message = str(sentences[0])[:150] if sentences else articles[-1].title[:150]

    return message, detail
```

### 5. Catch Me Up Feature (Template-Based)

```python
def generate_catchup(cluster: Cluster, commits: list[Commit]) -> str:
    """
    Generate a structured narrative from commits using templates.
    No LLM required — extractive + templated.
    """
    if not commits:
        return "No developments to report yet."

    sorted_commits = sorted(commits, key=lambda c: c.commit_date)
    total = len(sorted_commits)

    # Opening
    first = sorted_commits[0]
    first_date = first.commit_date.strftime("%B %d")
    narrative = f"This story began on {first_date}. {first.detail}\n\n"

    # Middle (key developments)
    if total > 2:
        middle_commits = sorted_commits[1:-1]
        # Pick up to 3 most spaced-out commits
        step = max(len(middle_commits) // 3, 1)
        key_moments = middle_commits[::step][:3]

        narrative += "Key developments since then:\n"
        for c in key_moments:
            date = c.commit_date.strftime("%b %d")
            narrative += f"• {date}: {c.message}\n"
        narrative += "\n"

    # Closing
    last = sorted_commits[-1]
    last_date = last.commit_date.strftime("%B %d")
    narrative += f"Most recently, on {last_date}: {last.detail}"

    return narrative
```

**Why templates over LLM:**
- Mistral 7B (quantized) needs ~4–8 GB RAM — impossible on Railway free tier (512 MB).
- Ollama itself is an additional service to deploy and manage.
- Template output is deterministic, fast (<10 ms), and never hallucinates.
- Trade-off: Less fluid prose. For an MVP targeting 3–5 minute catch-ups, structured bullet points are arguably better than LLM prose anyway.

**Post-MVP upgrade path**: When you have budget for a GPU instance or an API key (OpenAI/Anthropic), swap `generate_catchup()` with an LLM call. The interface stays the same.

---

## API Specification (FastAPI)

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stories` | List active story clusters (paginated, sorted by heat) |
| `GET` | `/api/stories/{id}` | Story detail with recent commits |
| `GET` | `/api/stories/{id}/commits` | Full commit log (paginated) |
| `GET` | `/api/stories/{id}/catchup` | Get catch-up narrative (GET, not POST — no state change) |
| `GET` | `/api/search?q=` | Full-text search across articles |
| `GET` | `/api/health` | Health check + last ingestion timestamp |

### Response Schemas

```python
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class StoryCard(BaseModel):
    id: UUID
    topic_label: str
    latest_commit_message: str
    heat_score: float
    state: str
    article_count: int
    last_updated: datetime

class StoryDetail(BaseModel):
    id: UUID
    topic_label: str
    state: str
    heat_score: float
    article_count: int
    commits: list["CommitResponse"]
    created_at: datetime
    updated_at: datetime

class CommitResponse(BaseModel):
    id: UUID
    message: str
    detail: str
    commit_date: datetime
    source_count: int
    source_urls: list[str]

class CatchUpResponse(BaseModel):
    story_id: UUID
    narrative: str
    commit_count: int
    time_span_days: int

class HealthResponse(BaseModel):
    status: str                   # "ok" | "degraded"
    last_ingestion: datetime | None
    active_stories: int
    total_articles: int
```

### Error Handling

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

# Standard error shape
class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None

# Global exception handler
@app.exception_handler(Exception)
async def global_handler(request, exc):
    logger.exception(f"Unhandled: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": None}
    )

# Per-endpoint example
@app.get("/api/stories/{story_id}")
async def get_story(story_id: UUID, db: AsyncSession = Depends(get_db)):
    story = await db.get(Cluster, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    # ...
```

### Middleware

```python
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

# CORS — allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",          # Dev
        "https://chronicle-ai.vercel.app" # Prod (update with actual domain)
    ],
    allow_methods=["GET"],                # Read-only API for MVP
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/stories")
@limiter.limit("30/minute")
async def list_stories(request: Request, ...):
    ...
```

### Caching Strategy

```python
from functools import lru_cache
from datetime import datetime, timedelta

# In-memory cache for dashboard (refreshed every 5 min)
_stories_cache = {"data": None, "expires_at": datetime.min}

async def get_cached_stories(db: AsyncSession):
    now = datetime.utcnow()
    if _stories_cache["data"] and now < _stories_cache["expires_at"]:
        return _stories_cache["data"]

    stories = await fetch_active_stories(db)
    _stories_cache["data"] = stories
    _stories_cache["expires_at"] = now + timedelta(minutes=5)
    return stories
```

**Why in-memory over Redis cache**: No Redis in the stack. For a single-process app with <500 users, Python-level caching is sufficient. Dashboard data changes every 30 min (ingestion interval), so a 5-minute TTL is fine.

---

## Frontend Specification (Next.js 14)

### Pages

```
/                     → Dashboard (topic cards sorted by heat)
/story/[id]           → Story detail (commit log)
```

**No `/api` routes in Next.js** — all data comes from the FastAPI backend. Next.js is a pure rendering layer.

### Component Architecture

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx                    # Dashboard
│   │   ├── layout.tsx                  # Root layout + navbar
│   │   └── story/
│   │       └── [id]/
│   │           └── page.tsx            # Story detail + catch-up
│   ├── components/
│   │   ├── ui/                         # shadcn/ui components
│   │   ├── StoryCard.tsx               # Dashboard topic card
│   │   ├── CommitLog.tsx               # Git-style commit list
│   │   ├── CatchUpPanel.tsx            # Catch-up narrative display
│   │   ├── HeatBadge.tsx               # Heat score indicator
│   │   ├── SearchBar.tsx               # Full-text search
│   │   └── Navbar.tsx                  # Top navigation
│   ├── lib/
│   │   ├── api.ts                      # Typed fetch wrapper for FastAPI
│   │   └── utils.ts                    # Date formatting, etc.
│   └── styles/
│       └── globals.css                 # Tailwind imports
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.js
```

### Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│  Chronicle AI                        [🔍 Search]     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │  India-Pakistan     │  │  Gaza Ceasefire     │  │
│  │  tensions           │  │  talks              │  │
│  │  "India closes      │  │  "Mediators resume  │  │
│  │   airspace to..."   │  │   negotiations..."  │  │
│  │  🔴 Active  2h ago  │  │  🟡 Cooling  5h ago │  │
│  └─────────────────────┘  └─────────────────────┘  │
│                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │  US Election 2026   │  │  Climate Summit     │  │
│  │  1d ago             │  │  3h ago             │  │
│  └─────────────────────┘  └─────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Story Detail Layout

```
┌─────────────────────────────────────────────────────┐
│  ← Back          India-Pakistan tensions             │
├─────────────────────────────────────────────────────┤
│  [ Catch Me Up ]                     🔴 Active       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Apr 18 ┬── India closes airspace to Pakistani...   │
│         │   India has ordered the closure of its    │
│         │   airspace to all Pakistani aircraft...   │
│         │   Sources: Reuters, BBC                   │
│         │                                           │
│  Apr 16 ┬── 26 tourists killed in Pahalgam...       │
│         │   Armed militants opened fire on tourists │
│         │   in Pahalgam, Kashmir...                 │
│         │   Sources: AP, NDTV                       │
│         │                                           │
│  Mar 02 ┬── Pakistan PM calls for resumed trade...  │
│         │   Pakistan's PM has called for the        │
│         │   resumption of trade talks...            │
│         │   Sources: The Hindu                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### UI Setup

```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card dialog scroll-area badge skeleton
```

### Data Fetching Pattern

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchStories(): Promise<StoryCard[]> {
  const res = await fetch(`${API_BASE}/api/stories`, {
    next: { revalidate: 300 }, // ISR: revalidate every 5 min
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchStory(id: string): Promise<StoryDetail> {
  const res = await fetch(`${API_BASE}/api/stories/${id}`, {
    next: { revalidate: 60 }, // Revalidate every minute for active stories
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchCatchUp(id: string): Promise<CatchUpResponse> {
  const res = await fetch(`${API_BASE}/api/stories/${id}/catchup`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

---

## Data Retention & Cleanup

```python
async def cleanup_old_articles(db: AsyncSession):
    """
    Run daily at 3 AM UTC.
    - Delete articles older than 30 days that belong to hibernated clusters.
    - Preserve articles in active/cooling clusters regardless of age.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    await db.execute(
        delete(Article).where(
            Article.published_at < cutoff,
            Article.cluster_id.in_(
                select(Cluster.id).where(Cluster.state == 'hibernated')
            )
        )
    )

    # Delete hibernated clusters with no remaining articles
    await db.execute(
        delete(Cluster).where(
            Cluster.state == 'hibernated',
            ~Cluster.id.in_(select(Article.cluster_id).where(Article.cluster_id.isnot(None)))
        )
    )

    await db.commit()
    logger.info(f"Cleanup complete: removed articles before {cutoff}")
```

**Why 30 days**: Railway free tier has 1 GB storage. At ~200 articles/day × 30 days = ~6,000 articles. With average 2 KB per row, that's ~12 MB. Well within limits, with room for indexes.

---

## Deployment

### Environment Variables

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/chronicle
FRONTEND_URL=http://localhost:3000

# Production overrides
# DATABASE_URL=postgresql+asyncpg://...@railway/chronicle
# FRONTEND_URL=https://chronicle-ai.vercel.app
```

### Docker Compose (Development)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: chronicle
      POSTGRES_USER: chronicle
      POSTGRES_PASSWORD: chronicle_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://chronicle:chronicle_dev@postgres:5432/chronicle
      FRONTEND_URL: http://localhost:3000
    depends_on:
      - postgres
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - backend

volumes:
  pgdata:
```

**Removed**: Redis service (no Celery), pgvector image (standard Postgres).

### Production Deployment

| Component | Platform | Free Tier |
|-----------|----------|-----------|
| Backend (FastAPI + scheduler) | Railway | 512 MB RAM, 1 GB disk |
| Frontend (Next.js) | Vercel | 100 GB bandwidth |
| Database (PostgreSQL) | Railway | 1 GB storage |

**Total services: 3** (down from 5 in original: backend, frontend, postgres, ~~redis~~, ~~ollama~~).

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install spaCy model at build time
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Monitoring (Minimal)

```python
import logging
import time
from fastapi import Request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("chronicle")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    if duration > 2.0:  # Log slow requests
        logger.warning(f"SLOW {request.method} {request.url.path} {duration:.2f}s")
    return response
```

---

## Implementation Timeline (8 Weeks)

### Phase 1: Foundation (Weeks 1–2)
- [ ] Set up PostgreSQL schema with migrations (Alembic)
- [ ] FastAPI project structure with async SQLAlchemy
- [ ] RSS ingestion service with feedparser
- [ ] APScheduler integration
- [ ] Article deduplication by URL hash
- [ ] Health endpoint
- [ ] Docker Compose for local dev

### Phase 2: Clustering + Summaries (Weeks 3–4)
- [ ] TF-IDF + KMeans clustering pipeline
- [ ] spaCy NER entity extraction (`en_core_web_sm`)
- [ ] Entity fingerprint for cross-temporal linking
- [ ] Heat score calculation + state transitions
- [ ] LexRank commit generation (sumy)
- [ ] Topic label extraction from TF-IDF keywords

### Phase 3: API + Frontend (Weeks 5–7)
- [ ] All REST endpoints with error handling
- [ ] CORS, rate limiting middleware
- [ ] In-memory caching for dashboard
- [ ] Next.js dashboard with story cards
- [ ] Story detail page with commit log
- [ ] Catch Me Up panel (template-based)
- [ ] Search functionality
- [ ] Mobile-responsive design (Tailwind)
- [ ] shadcn/ui component integration

### Phase 4: Deploy + Polish (Week 8)
- [ ] Railway deployment (backend + postgres)
- [ ] Vercel deployment (frontend)
- [ ] Data retention cleanup job
- [ ] Request logging middleware
- [ ] End-to-end manual testing
- [ ] Bug fixes

---

## Acceptance Criteria (MVP)

### Must Have
- [ ] 5 RSS feeds ingested every 30 min without errors
- [ ] Articles deduplicated by URL hash
- [ ] TF-IDF + KMeans produces 10–20 meaningful clusters
- [ ] NER entity fingerprint links articles across days/weeks
- [ ] Heat score correctly transitions cluster states
- [ ] LexRank generates readable one-line commit messages + 3-sentence details
- [ ] Dashboard displays active topics sorted by heat
- [ ] Story detail shows chronological commit log with source attribution
- [ ] Catch Me Up generates structured narrative from commits
- [ ] Full-text search works across articles
- [ ] Mobile-responsive layout
- [ ] Deploys on Railway + Vercel free tier
- [ ] Handles <500 concurrent users without crashing

### Post-MVP Roadmap (not in scope)
- [ ] GDELT 2.0 integration for broader coverage
- [ ] SBERT embeddings + HDBSCAN for higher-quality clustering
- [ ] LLM-based Catch Me Up (OpenAI API or self-hosted)
- [ ] User accounts + follow/notify system
- [ ] Story branching (parent/child clusters)
- [ ] Sentiment analysis (VADER) with UI
- [ ] Activity sparklines on dashboard cards
- [ ] Breaking news push notifications
- [ ] NewsAPI backfill for historical data
- [ ] Multi-language support

---

## Known Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| TF-IDF clustering quality on live data | Medium | Tune `SIMILARITY_THRESHOLD` and `MIN_ARTICLES_TO_CLUSTER`. Add manual override for mislabeled clusters. Seed initial clusters from a curated list of active topics. |
| RSS feed downtime/format changes | Medium | Graceful per-feed error handling. Log failures. Remaining feeds continue. |
| Railway free-tier RAM limits | High | Profile memory usage. Batch clustering. Use `en_core_web_sm` (15 MB) not `en_core_web_trf` (500 MB). |
| Cold-start: no clusters on day 1 | Medium | Pre-seed with manually curated clusters for 5–10 major ongoing stories. |
| LexRank summary quality | Low | Extractive methods work well on news text. Fallback: use article title as commit message. |
| Single-process scheduler reliability | Medium | APScheduler persists missed jobs. Add last-run timestamp to health check. |

---

## Python Dependencies (backend/requirements.txt)

```
# Web framework
fastapi>=0.110.0
uvicorn[standard]>=0.27.0

# Database
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0

# Scheduling
apscheduler>=3.10.0

# RSS
feedparser>=6.0.0

# NLP
spacy>=3.7.0
sumy>=0.11.0
nltk>=3.8.0

# Clustering
scikit-learn>=1.4.0

# Rate limiting
slowapi>=0.1.9

# Utilities
python-dotenv>=1.0.0
pydantic>=2.6.0
pydantic-settings>=2.1.0
httpx>=0.27.0
```

**What was removed**: `sentence-transformers`, `hdbscan`, `bertopic`, `ollama`, `celery`, `redis`, `pgvector`, `vaderSentiment`. Total dependency footprint dropped by ~60%.

---

## File Structure

```
chronical-ai/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app + lifespan + scheduler
│   │   ├── config.py                # Pydantic Settings
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── article.py
│   │   │   ├── cluster.py
│   │   │   └── commit.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── story.py
│   │   │   └── commit.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── stories.py
│   │   │   ├── search.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py         # RSS fetching
│   │   │   ├── clustering.py        # TF-IDF + KMeans
│   │   │   ├── summarization.py     # LexRank + catchup templates
│   │   │   └── lifecycle.py         # Heat score + state machine
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── database.py          # Async engine + session
│   │       └── logging.py           # Logger config
│   ├── alembic/                     # DB migrations
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── styles/
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── next.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── prompt.md
```
