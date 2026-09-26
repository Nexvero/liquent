"""Add secret-free staging Research-index session-set registry.

Revision ID: 20260916_0044
Revises: 20260915_0043
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260916_0044"
down_revision: str | Sequence[str] | None = "20260915_0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staging_research_index_session_sets",
        sa.Column("session_set_id", sa.LargeBinary(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("session_set_id", name="pk_staging_research_index_session_sets"),
        sa.UniqueConstraint("revision_id", name="uq_staging_research_index_session_set_revision"),
        sa.CheckConstraint("length(session_set_id)>0", name="ck_staging_research_index_session_set_id"),
        sa.CheckConstraint("length(revision_id)>0", name="ck_staging_research_index_session_set_revision"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_staging_research_index_session_set_status"),
    )


def downgrade() -> None:
    op.drop_table("staging_research_index_session_sets")
