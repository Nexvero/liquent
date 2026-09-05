"""Add immutable terminal research-job outcomes.

Revision ID: 20260819_0027
Revises: 20260819_0026
"""

from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260819_0027"
down_revision: str | Sequence[str] | None = "20260819_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_job_outcomes",
        sa.Column("job_id", sa.LargeBinary(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=True),
        sa.Column("artifact_key", sa.Text(), nullable=True),
        sa.Column("artifact_sha256", sa.String(64), nullable=True),
        sa.Column("artifact_media_type", sa.String(128), nullable=True),
        sa.Column("artifact_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("failure_code", sa.String(32), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.job_id"]),
        sa.CheckConstraint("kind IN ('succeeded','failed')"),
        sa.CheckConstraint(
            "(kind='succeeded' AND summary_json IS NOT NULL AND artifact_key IS NOT NULL "
            "AND artifact_sha256 IS NOT NULL AND artifact_media_type IS NOT NULL "
            "AND artifact_size_bytes>0 AND failure_code IS NULL) OR "
            "(kind='failed' AND summary_json IS NULL AND artifact_key IS NULL "
            "AND artifact_sha256 IS NULL AND artifact_media_type IS NULL "
            "AND artifact_size_bytes IS NULL AND failure_code='execution_failed')"
        ),
    )


def downgrade() -> None:
    op.drop_table("research_job_outcomes")
