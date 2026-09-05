"""Add persistent absence and conflict recovery decisions.

Revision ID: 20260818_0023
Revises: 20260817_0022
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0023"
down_revision: str | Sequence[str] | None = "20260817_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_publication_recovery_decisions",
        sa.Column("recovery_id", sa.LargeBinary(), nullable=False),
        sa.Column("execution_id", sa.LargeBinary(), nullable=False),
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("kind", sa.String(length=17), nullable=False),
        sa.Column("current_authority", sa.Boolean(), nullable=False),
        sa.Column("external_artifact_id", sa.LargeBinary(), nullable=True),
        sa.Column("provider_revision", sa.LargeBinary(), nullable=True),
        sa.Column("reassessment_id", sa.LargeBinary(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("recovery_id", name="pk_release_publication_recovery"),
        sa.UniqueConstraint("execution_id", "attempt_id", name="uq_release_publication_recovery_attempt"),
        sa.ForeignKeyConstraint(["execution_id"], ["release_publication_executions.execution_id"], name="fk_release_recovery_execution"),
        sa.ForeignKeyConstraint(["attempt_id"], ["release_publication_execution_attempts.attempt_id"], name="fk_release_recovery_attempt"),
        sa.ForeignKeyConstraint(["reassessment_id"], ["release_publication_reassessments.reassessment_id"], name="fk_release_recovery_reassessment"),
        sa.CheckConstraint("kind IN ('absence_confirmed','conflict')", name="ck_release_recovery_kind"),
        sa.CheckConstraint(
            "(kind='absence_confirmed' AND external_artifact_id IS NULL "
            "AND provider_revision IS NULL AND reassessment_id IS NULL) OR "
            "(kind='conflict' AND external_artifact_id IS NOT NULL "
            "AND provider_revision IS NOT NULL AND reassessment_id IS NOT NULL)",
            name="ck_release_recovery_evidence",
        ),
    )


def downgrade() -> None:
    op.drop_table("release_publication_recovery_decisions")
