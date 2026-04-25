# Chronicle AI - Implementation Prompt

## Project Overview

**Chronicle AI** is a free, consumer-facing web application that automatically ingests, clusters, and narrates the news into clean chronological story timelines — one per topic. The core interaction model mirrors a GitHub commit log: each major development is a "commit" with a one-line summary, timestamp, and expandable three-sentence detail.

**Target User**: Working-class adults (nurses, drivers, retail workers, factory staff) who have 3-5 minutes during lunch breaks to stay informed about world events without needing to follow news daily.

**Core Constraint**: No accounts required. No infinite scroll. No algorithmic manipulation. Zero to minimal deployment cost.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHRONICLE AI SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   GDELT 2.0  │     │  RSS Feeds   │     │  NewsAPI    │                │
│  │  (Primary)   │     │ (BBC,Reuters)│     │ (Backfill)  │                │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              ▼                                              │
│              ┌───────────────────────────────┐                              │
│              │      INGESTION SERVICE        │                              │
│              │   (Celery Beat - every 15min) │                              │
│              │   - Deduplication by URL hash │                              │
│              │   - Store raw articles        │                              │
│              └───────────────┬───────────────┘                              │
│                              ▼                                              │
│              ┌───────────────────────────────┐                              │
│              │    CLUSTERING SERVICE         │                              │
│              │   (Celery Worker - hourly)    │                              │
│              │   1. SBERT embeddings         │                              │
│              │   2. HDBSCAN clustering       │                              │
│              │   3. NER entity linking       │                              │
│              │   4. Heat score calculation   │                              │
│              └───────────────┬───────────────┘                              │
│                              ▼                                              │
│              ┌───────────────────────────────┐                              │
│              │  SUMMARIZATION SERVICE        │                              │
│              │   (Triggered on cluster       │                              │
│              │    update)                    │                              │
│              │   - LexRank commit messages   │                              │
│              │   - BERTopic auto-labels      │                              │
│              └───────────────┬───────────────┘                              │
│                              ▼                                              │
│         ┌────────────────────┼────────────────────┐                         │
│         │                    │                    │                         │
│         ▼                    ▼                    ▼                         │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────┐                 │
│  │ PostgreSQL  │    │   pgvector      │    │  Ollama     │                 │
│  │ (Relations) │    │  (Embeddings)   │    │ (Mistral 7B)│                 │
│  └─────────────┘    └─────────────────┘    └─────────────┘                 │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              ▼                                              │
│              ┌───────────────────────────────┐                              │
│              │        FASTAPI SERVER         │                              │
│              │   (Always-on REST API)        │                              │
│              │   /stories, /commits,          │                              │
│              │   /catchup, /follow            │                              │
│              └───────────────┬───────────────┘                              │
│                              │                                              │
│                              ▼                                              │
│              ┌───────────────────────────────┐                              │
│              │       NEXT.JS 14 FRONTEND     │                              │
│              │   - Dashboard (topic cards)   │                              │
│              │   - Story log (commit view)   │                              │
│              │   - Catch Me Up modal         │                              │
│              │   - Sparklines & charts       │                              │
│              └───────────────────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

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
    content TEXT,
    source VARCHAR(255) NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    gkg_codes JSONB,          -- GDELT Global Knowledge Graph codes
    sentiment JSONB,          -- VADER sentiment scores
    location JSONB,           -- Geographic metadata
    embedding vector(384),    -- SBERT embedding (all-MiniLM-L6-v2)
    entities JSONB,           -- spaCy NER extracted entities
    cluster_id UUID REFERENCES clusters(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Story clusters table
CREATE TABLE clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_name VARCHAR(500) NOT NULL,      -- BERTopic-generated or manual
    gkg_seed_code VARCHAR(50),             -- GDELT GKG code for seeding
    state VARCHAR(20) DEFAULT 'active',    -- active, cooling, hibernated, branched
    heat_score FLOAT DEFAULT 0.0,
    parent_cluster_id UUID REFERENCES clusters(id), -- For branched stories
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_article_at TIMESTAMP WITH TIME ZONE
);

-- Commits table (one per story development)
CREATE TABLE commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID NOT NULL REFERENCES clusters(id),
    message TEXT NOT NULL,                 -- One-line LexRank summary
    detail TEXT NOT NULL,                  -- Three-sentence expansion
    article_ids UUID[] NOT NULL,           -- Source articles for this commit
    commit_date TIMESTAMP WITH TIME ZONE NOT NULL,
    sentiment JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users table (for follow/notify feature)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(500) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Followed topics
CREATE TABLE user_follows (
    user_id UUID NOT NULL REFERENCES users(id),
    cluster_id UUID NOT NULL REFERENCES clusters(id),
    notify_daily BOOLEAN DEFAULT true,
    notify_breaking BOOLEAN DEFAULT false,
    quiet_hours_start TIME DEFAULT '22:00',
    quiet_hours_end TIME DEFAULT '07:00',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, cluster_id)
);

-- Indexes
CREATE INDEX idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX idx_articles_cluster_id ON articles(cluster_id);
CREATE INDEX idx_articles_embedding ON articles USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_commits_cluster_id ON commits(cluster_id);
CREATE INDEX idx_commits_date ON commits(commit_date DESC);
CREATE INDEX idx_clusters_heat ON clusters(heat_score DESC);
CREATE INDEX idx_clusters_state ON clusters(state);
```

---

## Core Components Specification

### 1. Data Ingestion Service

**Objective**: Fetch articles from GDELT, RSS feeds, and NewsAPI without scraping.

#### GDELT 2.0 Integration
- Use `gdeltdoc` Python client
- Query GKG (Global Knowledge Graph) for English articles
- Fields: `title`, `seendate`, `url`, `domain`, `socialimage`, `tone`, `entities`
- Schedule: Every 15 minutes via Celery Beat
- Rate limit: Respect GDELT's free tier (15-minute refresh)

#### RSS Feed Sources
| Source | URL | Priority |
|--------|-----|----------|
| BBC World | `http://feeds.bbci.co.uk/news/world/rss.xml` | 1 |
| Reuters World | `https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best` | 1 |
| AP News | `https://feeds.apnews.com/apnews/topnews` | 1 |
| The Hindu | `https://www.thehindu.com/news/feeds/default/rssfeed.xml` | 2 |
| NDTV | `https://feeds.ndtv.com/ndrss/news` | 2 |

- Use `feedparser` library
- Extract: `title`, `summary`, `link`, `published`
- Schedule: Every 30 minutes

#### NewsAPI Integration (Optional Backfill)
- Free tier: 100 requests/day
- Use for gap coverage and historical backfill
- Store API key in environment variable: `NEWSAPI_KEY`

#### Deduplication Strategy
```python
def generate_url_hash(url: str) -> str:
    """SHA256 hash of normalized URL for deduplication."""
    normalized = url.split('?')[0].rstrip('/').lower()
    return hashlib.sha256(normalized.encode()).hexdigest()

# Check existence before insert
if not Article.exists(url_hash=url_hash):
    Article.create(...)
```

### 2. Clustering Service

**Objective**: Group related articles into story clusters across time.

#### Two-Stage Pipeline

**Stage 1: Semantic Embedding + HDBSCAN**
```python
# Sentence-BERT for embeddings
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_article(article: Article) -> np.ndarray:
    text = f"{article.title} {article.content[:500]}"
    return model.encode(text, normalize_embeddings=True)

# HDBSCAN clustering
import hdbscan

clusterer = hdbscan.HDBSCAN(
    min_cluster_size=5,
    min_samples=2,
    metric='cosine',
    cluster_selection_method='eom',
    prediction_data=True
)

clusters = clusterer.fit_predict(embeddings)
```

**Stage 2: Named Entity Linking (Cross-Temporal)**
```python
import spacy

nlp = spacy.load('en_core_web_trf')

def extract_entities(article: Article) -> List[str]:
    doc = nlp(f"{article.title} {article.content[:1000]}")
    entities = []
    for ent in doc.ents:
        if ent.label_ in ['PERSON', 'ORG', 'GPE', 'EVENT', 'FAC']:
            entities.append(ent.text.lower())
    return list(set(entities))

def compute_entity_overlap(article_entities: List[str], cluster_entities: List[str]) -> float:
    """Return overlap score between article and cluster entity fingerprints."""
    if not article_entities or not cluster_entities:
        return 0.0
    a_set = set(article_entities)
    c_set = set(cluster_entities)
    return len(a_set & c_set) / len(a_set | c_set)

# Decision logic
def should_link_to_cluster(article: Article, cluster: Cluster) -> bool:
    cosine_sim = compute_cosine_similarity(article.embedding, cluster.centroid)
    entity_overlap = compute_entity_overlap(article.entities, cluster.entity_fingerprint)
    
    # Must pass BOTH tests
    return cosine_sim > 0.6 and entity_overlap >= 0.25  # ≥2 shared entities
```

**Cluster Creation Rules**
- New cluster created if: no existing cluster passes the linking test
- Minimum 5 articles to form a stable cluster
- Each cluster stores: `entity_fingerprint` (Set[str]), `centroid` (np.ndarray)

### 3. Story Lifecycle Management

**Heat Score Formula**
```python
def calculate_heat_score(articles: List[Article], decay_lambda: float = 0.1) -> float:
    """
    H(t) = Σ articles × e^(-λ × Δt)
    λ = 0.1 (decay constant)
    Δt = days since article publication
    """
    now = datetime.utcnow()
    score = 0.0
    
    for article in articles:
        delta_days = (now - article.published_at).total_seconds() / 86400
        weight = math.exp(-decay_lambda * delta_days)
        
        # Source authority multiplier
        authority = {
            'bbc.com': 1.2,
            'reuters.com': 1.2,
            'apnews.com': 1.1,
            'thehindu.com': 1.0,
            'ndtv.com': 1.0,
        }.get(article.domain, 1.0)
        
        score += weight * authority
    
    return score
```

**State Machine**
```
┌─────────────────────────────────────────────────────────────────┐
│                        STATE TRANSITIONS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐  H > 10.0  ┌──────────┐                         │
│   │  ACTIVE  │───────────>│ COOLING  │                         │
│   └──────────┘            └────┬─────┘                         │
│        ▲                       │                                │
│        │   New article         │  H <= 3.0                      │
│        │   matches entity      │  for 7 days                    │
│        │   fingerprint         ▼                                │
│   ┌────┴─────┐            ┌────────────┐                        │
│   │REACTIVATED│<──────────│ HIBERNATED │                        │
│   └──────────┘  New       └────────────┘                        │
│     article     ▲                                               │
│     arrives     │                                               │
│        │        │                                               │
│        └────────┘                                               │
│                                                                 │
│   BRANCHED: Manual split or auto-detection of sub-event        │
│   (e.g., "India-Pakistan" → "Pahalgam attack" as child)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Thresholds**
| Threshold | Value | Description |
|-----------|-------|-------------|
| `ACTIVE_THRESHOLD` | 10.0 | Story appears on dashboard |
| `COOLING_THRESHOLD` | 3.0 | Story marked as "slowing down" |
| `HIBERNATION_DAYS` | 7 | Days below COOLING_THRESHOLD to hibernate |
| `ENTITY_OVERLAP_MIN` | 0.25 | Minimum entity overlap for linking |

### 4. Summarization Service

**LexRank for Commit Messages**
```python
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lexrank import LexRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

def generate_commit(articles: List[Article], count: int = 3) -> Tuple[str, str]:
    """Generate commit message (1 line) and detail (3 sentences)."""
    
    # Combine article content
    combined_text = "\n\n".join([
        f"{a.title}. {a.content[:500]}" 
        for a in articles[-10:]  # Last 10 articles
    ])
    
    parser = PlaintextParser.from_string(combined_text, Tokenizer("english"))
    stemmer = Stemmer("english")
    summarizer = LexRankSummarizer(stemmer)
    summarizer.stop_words = get_stop_words("english")
    
    # Get 3 sentences for detail
    detail_sentences = summarizer(parser.document, 3)
    detail = " ".join(str(s) for s in detail_sentences)
    
    # Commit message = first sentence (truncated)
    message = detail.split('.')[0][:100]
    
    return message, detail
```

**BERTopic for Auto-Labeling**
```python
from bertopic import BERTopic

# Initialize once, use for clustering
topic_model = BERTopic(
    embedding_model="all-MiniLM-L6-v2",
    nr_topics="auto",
    verbose=True
)

def label_cluster(articles: List[Article]) -> str:
    """Generate human-readable topic label."""
    texts = [a.title for a in articles]
    topics, probs = topic_model.fit_transform(texts)
    
    # Get most representative topic
    if topics[0] != -1:
        return topic_model.get_topic(topics[0])[0]._repr_html_()
    return "Uncategorized"
```

### 5. Catch Me Up Feature

**Ollama + Mistral 7B Integration**
```python
import ollama

def generate_catchup_narrative(cluster: Cluster, commits: List[Commit]) -> str:
    """Generate full narrative arc from day one to today."""
    
    # Build context from commits
    commit_summaries = []
    for commit in sorted(commits, key=lambda c: c.commit_date):
        date_str = commit.commit_date.strftime('%b %d')
        commit_summaries.append(f"- {date_str}: {commit.message}")
    
    context = "\n".join(commit_summaries[-20:])  # Last 20 events
    
    prompt = f"""You are a news journalist writing a brief summary.
Given the following timeline of events, write a 3-paragraph narrative 
that tells the complete story from the first event to the most recent.

Timeline:
{context}

Write in plain English, no jargon. Start with when this story began 
and end with the latest developments. Keep it under 300 words."""

    response = ollama.chat(
        model='mistral:7b-instruct-q4_K_S',  # Quantized for CPU
        messages=[{'role': 'user', 'content': prompt}]
    )
    
    return response['message']['content']
```

**Ollama Setup**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull quantized model (8GB RAM required, runs on CPU)
ollama pull mistral:7b-instruct-q4_K_S

# Verify
ollama list
```

---

## API Specification (FastAPI)

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stories` | List active story clusters (paginated) |
| `GET` | `/api/stories/{id}` | Get story details with commits |
| `GET` | `/api/stories/{id}/commits` | Get commit log for a story |
| `POST` | `/api/stories/{id}/catchup` | Generate catch-up narrative |
| `POST` | `/api/stories/{id}/follow` | Follow a story |
| `DELETE` | `/api/stories/{id}/follow` | Unfollow a story |
| `GET` | `/api/health` | Health check |

### Response Schemas

```python
# /api/stories response
class StoryCard(BaseModel):
    id: UUID
    topic_name: str
    current_summary: str          # LexRank of last 3 commits
    heat_score: float
    last_updated: datetime
    activity_sparkline: List[int]  # 7-day article counts

# /api/stories/{id} response
class StoryDetail(BaseModel):
    id: UUID
    topic_name: str
    state: str
    heat_score: float
    commits: List[Commit]
    branch_count: int
    created_at: datetime
    updated_at: datetime

class Commit(BaseModel):
    id: UUID
    message: str                  # One-line summary
    detail: str                   # Three-sentence expansion
    commit_date: datetime
    source_links: List[str]       # URLs to source articles
    sentiment: dict               # VADER scores

# /api/stories/{id}/catchup response
class CatchUpResponse(BaseModel):
    story_id: UUID
    narrative: str                # LLM-generated arc
    generated_at: datetime
```

---

## Frontend Specification (Next.js 14)

### Pages

```
/                   → Dashboard (list of topic cards)
/story/[id]         → Story detail (commit log)
/story/[id]/catchup → Catch-up modal
/api/stories        → API routes (if using App Router)
```

### Component Architecture

```
src/
├── app/
│   ├── page.tsx                    # Dashboard
│   ├── layout.tsx                  # Root layout
│   ├── story/
│   │   └── [id]/
│   │       ├── page.tsx            # Story detail
│   │       └── layout.tsx
│   └── api/
│       └── stories/
│           ├── route.ts            # GET /api/stories
│           └── [id]/
│               ├── route.ts        # GET /api/stories/[id]
│               ├── catchup/
│               │   └── route.ts    # POST /api/stories/[id]/catchup
│               └── follow/
│                   └── route.ts    # POST/DELETE follow
├── components/
│   ├── ui/                         # shadcn/ui components
│   ├── StoryCard.tsx               # Dashboard topic card
│   ├── CommitLog.tsx               # Git-style commit list
│   ├── Sparkline.tsx               # 7-day activity chart
│   ├── CatchUpModal.tsx            # Catch-up LLM modal
│   └── Navbar.tsx                  # Top navigation
├── lib/
│   ├── api.ts                      # API client
│   └── utils.ts                    # Utility functions
└── styles/
    └── globals.css                 # Tailwind imports
```

### Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│  Chronicle AI                          [Followed: 3] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │   India-Pakistan    │  │   Gaza Ceasefire    │  │
│  │   tensions ████░    │  │   talks     ███░░    │  │
│  │   2h ago    Heat: 45│  │   5h ago    Heat: 32│  │
│  └─────────────────────┘  └─────────────────────┘  │
│                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │   US Election 2026  │  │   Climate Summit    │  │
│  │   1d ago    Heat: 28│  │   3h ago    Heat: 21│  │
│  └─────────────────────┘  └─────────────────────┘  │
│                                                     │
│                   ... more topics                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Story Detail Layout

```
┌─────────────────────────────────────────────────────┐
│  ← Back          India-Pakistan tensions     ⚙️    │
├─────────────────────────────────────────────────────┤
│  [ Catch Me Up ]                                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Apr 18 ┬── India closes airspace to Pakistani...  │
│         │   India has ordered the closure of its   │
│         │   airspace to all Pakistani aircraft...  │
│         │   [Reuters] [BBC]                        │
│         │                                          │
│  Apr 16 ┬── 26 tourists killed in Pahalgam...      │
│         │   Armed militants opened fire on tourists│
│         │   in Pahalgam, Kashmir. India has blamed ││
│         │   Pakistan-backed militants for the...   │
│         │   [AP] [NDTV]                            │
│         │                                          │
│  Mar 02 ┬── Pakistan PM calls for resumed trade... │
│         │   Pakistan's PM has called for the       │
│         │   resumption of trade talks with India...│
│         │   [The Hindu]                            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### UI Requirements (shadcn/ui)

```bash
# Install shadcn/ui
npx shadcn-ui@latest init

# Install components
npx shadcn-ui@latest add button card dialog scroll-area badge skeleton
```

### Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        // ... shadcn variables
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
```

---

## Task Queue (Celery + Redis)

### Celery Configuration

```python
# backend/celery_app.py
from celery import Celery

celery_app = Celery(
    'chronicle',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
    include=['app.services.ingestion', 'app.services.clustering', 'app.services.summarization']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'ingest-every-15-minutes': {
            'task': 'app.services.ingestion.ingest_all',
            'schedule': 900.0,  # 15 minutes
        },
        'cluster-every-hour': {
            'task': 'app.services.clustering.run_clustering',
            'schedule': 3600.0,  # 1 hour
        },
        'cleanup-hibernated-daily': {
            'task': 'app.services.lifecycle.cleanup_hibernated',
            'schedule': 86400.0,  # 24 hours
        },
    }
)
```

### Task Definitions

```python
# backend/app/services/ingestion.py
@celery_app.task
def ingest_gdelt():
    """Fetch articles from GDELT."""
    # Implement GDELT API call
    pass

@celery_app.task
def ingest_rss():
    """Fetch articles from RSS feeds."""
    # Implement RSS parsing
    pass

@celery_app.task
def ingest_all():
    """Run all ingestion tasks."""
    ingest_gdelt.delay()
    ingest_rss.delay()

# backend/app/services/clustering.py
@celery_app.task
def run_clustering():
    """Run SBERT + HDBSCAN + NER pipeline."""
    # 1. Get unclustered articles
    # 2. Generate embeddings
    # 3. Run HDBSCAN
    # 4. Apply NER linking
    # 5. Update cluster heat scores
    pass

# backend/app/services/summarization.py
@celery_app.task
def generate_commit_for_cluster(cluster_id: UUID):
    """Generate LexRank commit for cluster update."""
    pass

@celery_app.task
def generate_catchup_async(cluster_id: UUID):
   """Async catch-up generation (for long-running LLM)."""
    pass
```

---

## Deployment

### Environment Variables

```bash
# .env
DATABASE_URL=postgresql://user:pass@host:5432/chronicle
REDIS_URL=redis://localhost:6379

# Optional: NewsAPI key
NEWSAPI_KEY=your_key_here

# Ollama (local)
OLLAMA_HOST=http://localhost:11434

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: chronicle
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/chronicle
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
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

### Production Deployment

| Component | Platform | Free Tier Limits |
|-----------|----------|------------------|
| Backend API | Railway | 500 hours/month, 512MB RAM |
| Frontend | Vercel | 100GB bandwidth, Serverless |
| Database | Railway PostgreSQL | 1GB storage |
| Redis | Railway Redis | 25MB storage |

---

## Implementation Phases

### Phase 1: Data Pipeline (Weeks 1-2)
- [ ] Set up PostgreSQL with pgvector extension
- [ ] Implement GDELT ingestion
- [ ] Implement RSS feed ingestion
- [ ] Set up Celery + Redis
- [ ] Article deduplication logic

### Phase 2: Clustering (Weeks 3-4)
- [ ] Sentence-BERT embedding pipeline
- [ ] HDBSCAN clustering
- [ ] spaCy NER integration
- [ ] Cross-temporal entity linking
- [ ] Heat score calculation

### Phase 3: Summarization (Weeks 5-6)
- [ ] LexRank commit generation
- [ ] BERTopic auto-labeling
- [ ] VADER sentiment analysis
- [ ] State machine implementation

### Phase 4: API + Frontend (Weeks 7-9)
- [ ] FastAPI backend with all endpoints
- [ ] Next.js dashboard
- [ ] Story detail page
- [ ] Commit log component
- [ ] Sparkline charts

### Phase 5: Catch-Up Feature (Week 10)
- [ ] Ollama setup
- [ ] Mistral 7B integration
- [ ] Catch-up modal UI

### Phase 6: Polish + Testing (Weeks 11-12)
- [ ] User testing
- [ ] Performance optimization
- [ ] Bug fixes
- [ ] Documentation

---

## Acceptance Criteria

### Must Have (MVP)
- [ ] GDELT + 5 RSS feeds ingested without errors
- [ ] Articles deduplicated by URL hash
- [ ] SBERT + HDBSCAN produces valid clusters
- [ ] NER linking maintains story coherence across weeks
- [ ] Heat score correctly transitions states
- [ ] LexRank generates readable commit messages
- [ ] Dashboard displays 15-20 active topics
- [ ] Story log shows chronological commits
- [ ] Mobile-responsive design
- [ ] Deploys on free-tier infrastructure

### Should Have
- [ ] BERTopic auto-labels stories
- [ ] Catch-up feature works with Ollama
- [ ] Follow/notify system functional
- [ ] Activity sparklines on cards

### Nice to Have
- [ ] NewsAPI backfill integration
- [ ] Breaking news notifications
- [ ] Multi-language support (future phase)

---

## Known Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Clustering quality on live data | Medium | Seed with GDELT GKG codes as ground truth |
| LLM catch-up cost at scale | Medium-High | Default to offline Ollama (quantized Mistral) |
| GDELT coverage gaps | Medium | Supplement with RSS feeds |
| Story boundary subjectivity | Low-Medium | Use GDELT EventCode hierarchy as canonical |
| Free-tier resource limits | High | Scope MVP to <500 daily users |

---

## References

1. Allan, J., Papka, R., & Lavrenko, V. (1998). On-line new event detection and tracking. SIGIR '98.
2. Sayyadi, H., & Getoor, L. (2009). Future event detection. - Exponential decay for event streams.
3. Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.
4. McInnes, L., Healy, J., & Astels, S. (2017). hdbscan: Hierarchical density based clustering. JOSS.
5. Erkan, G., & Radev, D. (2004). LexRank: Graph-based Lexical Centrality as Salience in Text Summarization.
6. GDELT Project Documentation - gdeltproject.org/data.html
7. Grootendorst, M. (2022). BERTopic: Neural topic modeling with class-based TF-IDF.

---

## File Structure

```
chronical-ai/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # Settings
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── article.py
│   │   │   ├── cluster.py
│   │   │   └── commit.py
│   │   ├── schemas/                # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── story.py
│   │   │   └── commit.py
│   │   ├── api/                    # API routes
│   │   │   ├── __init__.py
│   │   │   ├── stories.py
│   │   │   └── health.py
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py
│   │   │   ├── clustering.py
│   │   │   ├── summarization.py
│   │   │   └── lifecycle.py
│   │   └── core/                   # Core utilities
│   │       ├── __init__.py
│   │       ├── db.py
│   │       └── config.py
│   ├── celery_app.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── styles/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
└── prompt.md
```