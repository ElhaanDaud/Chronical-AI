import math
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from io import StringIO

import numpy as np
import spacy
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.article import Article
from app.models.cluster import Cluster
from app.models.commit import Commit

MIN_ARTICLES_TO_CLUSTER = 3
MAX_CLUSTERS = 25
SIMILARITY_THRESHOLD = 0.3
DECAY_LAMBDA = 0.15

_NOISE_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._fed: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        self._skip = tag in ("script", "style")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._fed.append(data)

    def get_text(self) -> str:
        return " ".join(self._fed)


def clean_text(html_str: str | None) -> str:
    if not html_str:
        return ""
    try:
        stripper = _HTMLStripper()
        stripper.feed(html_str)
        text = stripper.get_text()
    except Exception:
        text = html_str
    text = _NOISE_PATTERN.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


nlp = spacy.load("en_core_web_sm")


def extract_entities(text: str) -> list[str]:
    doc = nlp(text[:1000])
    return list(set(
        ent.text.lower()
        for ent in doc.ents
        if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT")
    ))


def entity_overlap_score(article_entities: list[str], cluster_entities: list[str]) -> float:
    if not article_entities or not cluster_entities:
        return 0.0
    a, c = set(article_entities), set(cluster_entities)
    return len(a & c) / len(a | c)


def calculate_heat(articles: list[Article], commits: list | None = None) -> float:
    now = datetime.now(timezone.utc)
    score = 0.0
    for article in articles:
        if article.published_at:
            delta_days = (now - article.published_at).total_seconds() / 86400
            score += math.exp(-DECAY_LAMBDA * max(delta_days, 0))

    if commits:
        ten_days_ago = now - timedelta(days=10)
        recent_commits = sum(1 for c in commits if c.commit_date >= ten_days_ago)
        score += 0.5 * recent_commits

    return round(score, 2)


def extract_topic_label(articles: list, vectorizer: TfidfVectorizer, tfidf_matrix, labels, target_label: int) -> str:
    cluster_indices = [i for i, l in enumerate(labels) if l == target_label]
    if not cluster_indices:
        return "Uncategorized"
    cluster_tfidf = tfidf_matrix[cluster_indices].mean(axis=0).A1
    feature_names = vectorizer.get_feature_names_out()
    top_indices = cluster_tfidf.argsort()[-4:][::-1]
    keywords = [feature_names[i] for i in top_indices]
    return " \u2014 ".join(keywords).title()


async def run_clustering(db: AsyncSession) -> int:
    result = await db.execute(
        select(Article).where(Article.cluster_id.is_(None))
    )
    unclustered = list(result.scalars().all())

    if not unclustered:
        logger.info("No unclustered articles to process")
        return 0

    for article in unclustered:
        text = f"{article.title} {clean_text(article.summary)}"
        article.entities = extract_entities(text)

    result = await db.execute(
        select(Cluster)
        .where(Cluster.state.in_(["active", "cooling"]))
        .options(selectinload(Cluster.articles), selectinload(Cluster.commits))
    )
    existing_clusters = list(result.scalars().all())

    assigned_count = 0
    unmatched = []

    if existing_clusters:
        cluster_texts = []
        for cluster in existing_clusters:
            recent_articles = sorted(cluster.articles, key=lambda a: a.published_at, reverse=True)[:20]
            combined = " ".join(f"{a.title} {clean_text(a.summary)}" for a in recent_articles)
            cluster_texts.append(combined)

        article_texts = [f"{a.title} {clean_text(a.summary)}" for a in unclustered]
        all_texts = cluster_texts + article_texts

        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        cluster_vecs = tfidf_matrix[:len(existing_clusters)]
        article_vecs = tfidf_matrix[len(existing_clusters):]

        sim_matrix = cosine_similarity(article_vecs, cluster_vecs)

        for i, article in enumerate(unclustered):
            sims = sim_matrix[i]

            entity_scores = np.array([
                entity_overlap_score(article.entities, existing_clusters[j].entity_fingerprint or [])
                for j in range(len(existing_clusters))
            ])
            combined_scores = 0.7 * sims + 0.3 * entity_scores

            best_idx = int(np.argmax(combined_scores))

            if combined_scores[best_idx] >= SIMILARITY_THRESHOLD:
                best_cluster = existing_clusters[best_idx]
                article.cluster_id = best_cluster.id

                cluster_entities = set(best_cluster.entity_fingerprint or [])
                cluster_entities.update(article.entities)
                best_cluster.entity_fingerprint = list(cluster_entities)
                candidates = [t for t in (article.published_at, best_cluster.last_article_at) if t is not None]
                if candidates:
                    best_cluster.last_article_at = max(candidates)
                best_cluster.updated_at = datetime.now(timezone.utc)
                assigned_count += 1
            else:
                unmatched.append(article)
    else:
        unmatched = unclustered

    new_clusters_count = 0

    if len(unmatched) >= MIN_ARTICLES_TO_CLUSTER:
        texts = [f"{a.title} {clean_text(a.summary)}" for a in unmatched]
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        tfidf = vectorizer.fit_transform(texts)

        n_clusters = min(len(unmatched) // MIN_ARTICLES_TO_CLUSTER, MAX_CLUSTERS)
        n_clusters = max(n_clusters, 1)

        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=100)
        labels = kmeans.fit_predict(tfidf)

        for label in set(labels):
            group = [unmatched[i] for i, l in enumerate(labels) if l == label]
            if len(group) >= MIN_ARTICLES_TO_CLUSTER:
                topic_label = extract_topic_label(unmatched, vectorizer, tfidf, labels, label)

                all_entities = set()
                latest_article_at = None
                for a in group:
                    all_entities.update(a.entities or [])
                    if latest_article_at is None or a.published_at > latest_article_at:
                        latest_article_at = a.published_at

                new_cluster = Cluster(
                    topic_label=topic_label,
                    entity_fingerprint=list(all_entities),
                    heat_score=calculate_heat(group),
                    last_article_at=latest_article_at,
                )
                db.add(new_cluster)
                await db.flush()

                for article in group:
                    article.cluster_id = new_cluster.id

                new_clusters_count += 1

    await db.flush()

    for cluster in existing_clusters:
        await db.refresh(cluster, attribute_names=["articles", "commits"])
        cluster.heat_score = calculate_heat(cluster.articles, cluster.commits)

    await db.commit()

    logger.info(
        f"Clustering complete: {assigned_count} assigned to existing, "
        f"{new_clusters_count} new clusters, "
        f"{len(unmatched) - sum(1 for a in unmatched if a.cluster_id is not None)} unmatched"
    )
    return assigned_count + new_clusters_count
