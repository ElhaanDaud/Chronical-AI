import asyncio
import math
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

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
SIMILARITY_THRESHOLD = 0.55
DECAY_LAMBDA = 0.15
COHERENCE_THRESHOLD = 0.4

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


def _tfidf_topic_label(articles: list, vectorizer: TfidfVectorizer, tfidf_matrix, labels, target_label: int) -> str:
    cluster_indices = [i for i, l in enumerate(labels) if l == target_label]
    if not cluster_indices:
        return "Uncategorized"
    cluster_tfidf = tfidf_matrix[cluster_indices].mean(axis=0).A1
    feature_names = vectorizer.get_feature_names_out()
    top_indices = cluster_tfidf.argsort()[-4:][::-1]
    keywords = [feature_names[i] for i in top_indices]
    return " — ".join(keywords).title()


async def _get_article_embeddings(texts: list[str]) -> np.ndarray | None:
    from app.services.llm import get_embeddings
    return await get_embeddings(texts)


async def _llm_topic_label(titles: list[str], fallback: str) -> str:
    from app.services.llm import generate_topic_label
    label = await generate_topic_label(titles)
    return label if label else fallback


async def _llm_coherence_check(titles: list[str]) -> float:
    from app.services.llm import score_coherence
    return await score_coherence(titles)


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

        embeddings = await _get_article_embeddings(all_texts)
        use_embeddings = embeddings is not None

        if use_embeddings:
            logger.info("Using dense embeddings for clustering (DMR)")
            cluster_vecs = embeddings[:len(existing_clusters)]
            article_vecs = embeddings[len(existing_clusters):]
            sim_matrix = cosine_similarity(article_vecs, cluster_vecs)
        else:
            logger.info("Falling back to TF-IDF for clustering")
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

        unmatched_embeddings = await _get_article_embeddings(texts)
        use_embeddings_pass2 = unmatched_embeddings is not None

        if use_embeddings_pass2:
            from sklearn.metrics.pairwise import pairwise_distances
            distance_matrix = pairwise_distances(unmatched_embeddings, metric="cosine")
            n_clusters = min(len(unmatched) // MIN_ARTICLES_TO_CLUSTER, MAX_CLUSTERS)
            n_clusters = max(n_clusters, 1)
            kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=100)
            kmeans.fit(unmatched_embeddings)
            labels = kmeans.labels_
            vectorizer_pass2 = None
            tfidf_pass2 = None
        else:
            vectorizer_pass2 = TfidfVectorizer(stop_words="english", max_features=5000)
            tfidf_pass2 = vectorizer_pass2.fit_transform(texts)
            n_clusters = min(len(unmatched) // MIN_ARTICLES_TO_CLUSTER, MAX_CLUSTERS)
            n_clusters = max(n_clusters, 1)
            kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=100)
            labels = kmeans.fit_predict(tfidf_pass2)

        _llm_semaphore = asyncio.Semaphore(6)

        async def _process_candidate_group(label_id, group, vectorizer_pass2, tfidf_pass2, labels):
            async with _llm_semaphore:
                group_titles = [a.title for a in group]
                coherence = await _llm_coherence_check(group_titles)
                if coherence < COHERENCE_THRESHOLD:
                    logger.info(f"Rejected cluster (coherence {coherence:.2f}): {group_titles[:3]}")
                    return None

                tfidf_fallback = "Uncategorized"
                if vectorizer_pass2 is not None and tfidf_pass2 is not None:
                    tfidf_fallback = _tfidf_topic_label(unmatched, vectorizer_pass2, tfidf_pass2, labels, label_id)

                topic_label = await _llm_topic_label(group_titles, tfidf_fallback)

                all_entities = set()
                latest_article_at = None
                for a in group:
                    all_entities.update(a.entities or [])
                    if a.published_at and (latest_article_at is None or a.published_at > latest_article_at):
                        latest_article_at = a.published_at

                return {
                    "topic_label": topic_label,
                    "entities": list(all_entities),
                    "heat_score": calculate_heat(group),
                    "last_article_at": latest_article_at,
                    "articles": group,
                }

        candidate_groups = []
        for label in set(labels):
            group = [unmatched[i] for i, l in enumerate(labels) if l == label]
            if len(group) < MIN_ARTICLES_TO_CLUSTER:
                continue
            candidate_groups.append((label, group))

        results = await asyncio.gather(*[
            _process_candidate_group(label_id, group, vectorizer_pass2, tfidf_pass2, labels)
            for label_id, group in candidate_groups
        ])

        for result in results:
            if result is None:
                continue

            new_cluster = Cluster(
                topic_label=result["topic_label"],
                entity_fingerprint=result["entities"],
                heat_score=result["heat_score"],
                last_article_at=result["last_article_at"],
            )
            db.add(new_cluster)
            await db.flush()

            for article in result["articles"]:
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
