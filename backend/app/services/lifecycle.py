from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.cluster import Cluster
from app.services.clustering import calculate_heat

ACTIVE_THRESHOLD = 3.0
COOLING_THRESHOLD = 1.0
HIBERNATION_DAYS = 3


def determine_state(heat_score: float, current_state: str, last_article_at: datetime | None) -> str:
    if heat_score >= ACTIVE_THRESHOLD:
        return "active"

    if heat_score >= COOLING_THRESHOLD:
        return "cooling"

    if last_article_at:
        days_since = (datetime.now(timezone.utc) - last_article_at).total_seconds() / 86400
        if days_since >= HIBERNATION_DAYS:
            return "hibernated"

    if current_state == "hibernated":
        return "hibernated"

    return "cooling"


async def run_lifecycle(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(Cluster)
        .options(selectinload(Cluster.articles))
    )
    clusters = list(result.scalars().all())

    transitions = {"active": 0, "cooling": 0, "hibernated": 0}

    for cluster in clusters:
        new_heat = calculate_heat(cluster.articles)
        cluster.heat_score = new_heat

        new_state = determine_state(new_heat, cluster.state, cluster.last_article_at)
        if new_state != cluster.state:
            logger.info(
                f"Cluster '{cluster.topic_label}' state: {cluster.state} -> {new_state} "
                f"(heat: {new_heat})"
            )
            cluster.state = new_state
            transitions[new_state] += 1

    await db.commit()

    logger.info(
        f"Lifecycle complete: {transitions['active']} reactivated, "
        f"{transitions['cooling']} moved to cooling, "
        f"{transitions['hibernated']} hibernated"
    )
    return transitions
