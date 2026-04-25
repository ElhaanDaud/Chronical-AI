from datetime import datetime, timezone

from sumy.nlp.stemmers import Stemmer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.utils import get_stop_words
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.article import Article
from app.models.cluster import Cluster
from app.models.commit import Commit


def generate_commit(articles: list[Article]) -> tuple[str, str]:
    recent = sorted(articles, key=lambda a: a.published_at, reverse=True)[:10]
    combined = "\n\n".join(
        f"{a.title}. {a.summary or ''}"
        for a in recent
    )

    if not combined.strip():
        title = recent[0].title if recent else "No title"
        return title[:150], title

    parser = PlaintextParser.from_string(combined, Tokenizer("english"))
    summarizer = LexRankSummarizer(Stemmer("english"))
    summarizer.stop_words = get_stop_words("english")

    sentences = summarizer(parser.document, 3)

    if not sentences:
        title = recent[0].title if recent else "No title"
        return title[:150], title

    detail = " ".join(str(s) for s in sentences)
    message = str(sentences[0])[:150]

    return message, detail


def generate_catchup(commits: list[Commit]) -> str:
    if not commits:
        return "No developments to report yet."

    sorted_commits = sorted(commits, key=lambda c: c.commit_date)
    total = len(sorted_commits)

    first = sorted_commits[0]
    first_date = first.commit_date.strftime("%B %d")
    narrative = f"This story began on {first_date}. {first.detail}\n\n"

    if total > 2:
        middle_commits = sorted_commits[1:-1]
        step = max(len(middle_commits) // 3, 1)
        key_moments = middle_commits[::step][:3]

        narrative += "Key developments since then:\n"
        for c in key_moments:
            date = c.commit_date.strftime("%b %d")
            narrative += f"\u2022 {date}: {c.message}\n"
        narrative += "\n"

    last = sorted_commits[-1]
    last_date = last.commit_date.strftime("%B %d")
    narrative += f"Most recently, on {last_date}: {last.detail}"

    return narrative


async def run_summarization(db: AsyncSession) -> int:
    result = await db.execute(
        select(Cluster)
        .where(Cluster.state.in_(["active", "cooling"]))
        .options(selectinload(Cluster.articles), selectinload(Cluster.commits))
    )
    clusters = list(result.scalars().all())

    commits_created = 0

    for cluster in clusters:
        if not cluster.articles:
            continue

        existing_article_ids = set()
        for commit in cluster.commits:
            existing_article_ids.update(commit.article_ids or [])

        new_articles = [a for a in cluster.articles if a.id not in existing_article_ids]

        if len(new_articles) < 2:
            continue

        message, detail = generate_commit(new_articles)

        commit = Commit(
            cluster_id=cluster.id,
            message=message,
            detail=detail,
            article_ids=[a.id for a in new_articles],
            commit_date=max(a.published_at for a in new_articles),
        )
        db.add(commit)
        commits_created += 1

    await db.commit()
    logger.info(f"Summarization complete: {commits_created} new commits generated")
    return commits_created
