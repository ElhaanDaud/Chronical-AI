import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.cluster import Base


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clusters.id", ondelete="CASCADE"),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(String(150), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    article_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )
    commit_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cluster: Mapped["Cluster"] = relationship(back_populates="commits")
