import math
from datetime import datetime, timezone

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

MIN_ARTICLES_TO_CLUSTER = 3
MAX_CLUSTERS = 25
SIMILARITY_THRESHOLD = 0.3
DECAY_LAMBDA = 0.15

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


def calculate_heat(articles: list[Article]) -> float:
    now = datetime.now(timezone.utc)
    score = 0.0
    for article in articles:
        if article.published_at:
            delta_days = (now - article.published_at).total_seconds() / 86400
            score += math.exp(-DECAY_LAMBDA * max(delta_days, 0))
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
        text = f"{article.title} {article.summary or ''}"
        article.entities = extract_entities(text)

    result = await db.execute(
        select(Cluster)
        .where(Cluster.state.in_(["active", "cooling"]))
        .options(selectinload(Cluster.articles))
    )
    existing_clusters = list(result.scalars().all())

    assigned_count = 0
    unmatched = []

    if existing_clusters:
        cluster_text_map = {}
        all_texts = []

        for cluster in existing_clusters:
            recent_articles = sorted(cluster.articles, key=lambda a: a.published_at, reverse=True)[:20]
            combined = " ".join(f"{a.title} {a.summary or ''}" for a in recent_articles)
            cluster_text_map[cluster.id] = len(all_texts)
            all_texts.append(combined)

        for article in unclustered:
            article_text = f"{article.title} {article.summary or ''}"
            texts_with_article = all_texts + [article_text]

            vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
            tfidf_matrix = vectorizer.fit_transform(texts_with_article)

            article_vec = tfidf_matrix[-1]
            cluster_vecs = tfidf_matrix[:-1]

            sims = cosine_similarity(article_vec, cluster_vecs).flatten()

            entity_scores = np.array([
                entity_overlap_score(article.entities, existing_clusters[i].entity_fingerprint or [])
                for i in range(len(existing_clusters))
            ])
            combined_scores = 0.7 * sims + 0.3 * entity_scores

            best_idx = int(np.argmax(combined_scores))

            if combined_scores[best_idx] >= SIMILARITY_THRESHOLD:
                best_cluster = existing_clusters[best_idx]
                article.cluster_id = best_cluster.id

                cluster_entities = set(best_cluster.entity_fingerprint or [])
                cluster_entities.update(article.entities)
                best_cluster.entity_fingerprint = list(cluster_entities)
                best_cluster.last_article_at = max(
                    article.published_at,
                    best_cluster.last_article_at or article.published_at,
                )
                assigned_count += 1
            else:
                unmatched.append(article)
    else:
        unmatched = unclustered

    new_clusters_count = 0

    if len(unmatched) >= MIN_ARTICLES_TO_CLUSTER:
        texts = [f"{a.title} {a.summary or ''}" for a in unmatched]
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

    for cluster in existing_clusters:
        all_articles = cluster.articles + [a for a in unclustered if a.cluster_id == cluster.id]
        cluster.heat_score = calculate_heat(all_articles)

    await db.commit()

    logger.info(
        f"Clustering complete: {assigned_count} assigned to existing, "
        f"{new_clusters_count} new clusters, "
        f"{len(unmatched) - sum(1 for a in unmatched if a.cluster_id is not None)} unmatched"
    )
    return assigned_count + new_clusters_count
