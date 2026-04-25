import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_label: Mapped[str] = mapped_column(String(500), nullable=False)
    state: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("state IN ('active', 'cooling', 'hibernated')"),
        default="active",
    )
    heat_score: Mapped[float] = mapped_column(Float, default=0.0)
    entity_fingerprint: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_article_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    articles: Mapped[list["Article"]] = relationship(back_populates="cluster")
    commits: Mapped[list["Commit"]] = relationship(
        back_populates="cluster", cascade="all, delete-orphan"
    )
