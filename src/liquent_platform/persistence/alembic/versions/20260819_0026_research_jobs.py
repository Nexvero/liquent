"""Add persistent research jobs, acceptances, and current claims.

Revision ID: 20260819_0026
Revises: 20260819_0025
"""

from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260819_0026"
down_revision: str | Sequence[str] | None = "20260819_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_jobs",
        sa.Column("job_id", sa.LargeBinary(), primary_key=True),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("artifact_class", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["identity_users.user_id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["identity_workspaces.workspace_id"]),
        sa.CheckConstraint("status IN ('queued','running','succeeded','failed','invalidated','cancelled')"),
    )
    op.create_index("ix_research_jobs_queue", "research_jobs", ["status", "accepted_at", "job_id"])
    op.create_table(
        "research_job_acceptances",
        sa.Column("acceptance_id", sa.LargeBinary(), primary_key=True),
        sa.Column("job_id", sa.LargeBinary(), nullable=False, unique=True),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.job_id"]),
    )
    op.create_table(
        "research_job_claims",
        sa.Column("job_id", sa.LargeBinary(), primary_key=True),
        sa.Column("claim_id", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column("worker_id", sa.LargeBinary(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.job_id"]),
    )


def downgrade() -> None:
    op.drop_table("research_job_claims")
    op.drop_table("research_job_acceptances")
    op.drop_index("ix_research_jobs_queue", table_name="research_jobs")
    op.drop_table("research_jobs")
