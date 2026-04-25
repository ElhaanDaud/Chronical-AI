"""Initial schema: articles, clusters, commits with indexes and search trigger

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-04-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clusters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("topic_label", sa.String(500), nullable=False),
        sa.Column("state", sa.String(20), server_default="active", nullable=False),
        sa.Column("heat_score", sa.Float, server_default="0.0"),
        sa.Column("entity_fingerprint", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_article_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("state IN ('active', 'cooling', 'hibernated')", name="ck_clusters_state"),
    )

    op.create_table(
        "articles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("url", sa.String(2048), unique=True, nullable=False),
        sa.Column("url_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("entities", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("cluster_id", UUID(as_uuid=True), sa.ForeignKey("clusters.id"), nullable=True),
        sa.Column("search_vector", TSVECTOR, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "commits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cluster_id", UUID(as_uuid=True), sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.String(150), nullable=False),
        sa.Column("detail", sa.Text, nullable=False),
        sa.Column("article_ids", ARRAY(UUID(as_uuid=True)), nullable=False),
        sa.Column("commit_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("idx_articles_published", "articles", [sa.text("published_at DESC")])
    op.create_index("idx_articles_cluster", "articles", ["cluster_id"])
    op.create_index("idx_articles_search", "articles", ["search_vector"], postgresql_using="gin")
    op.create_index("idx_commits_cluster", "commits", ["cluster_id"])
    op.create_index("idx_commits_date", "commits", [sa.text("commit_date DESC")])
    op.create_index("idx_clusters_heat", "clusters", [sa.text("heat_score DESC")])
    op.create_index("idx_clusters_state", "clusters", ["state"])

    op.execute("""
        CREATE OR REPLACE FUNCTION articles_search_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.summary, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_articles_search
            BEFORE INSERT OR UPDATE ON articles
            FOR EACH ROW EXECUTE FUNCTION articles_search_trigger();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_articles_search ON articles")
    op.execute("DROP FUNCTION IF EXISTS articles_search_trigger()")

    op.drop_table("commits")
    op.drop_table("articles")
    op.drop_table("clusters")
