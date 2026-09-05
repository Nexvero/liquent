"""Add empty release-publication execution foundation.

Revision ID: 20260817_0022
Revises: 20260817_0021
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0022"
down_revision: str | Sequence[str] | None = "20260817_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_publication_executors",
        sa.Column("executor_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("executor_id", name="pk_release_publication_executors"),
        sa.CheckConstraint("length(executor_id)>0", name="ck_release_publication_executor_present"),
    )
    op.create_table(
        "release_publication_executions",
        sa.Column("execution_id", sa.LargeBinary(), nullable=False),
        sa.Column("handoff_id", sa.LargeBinary(), nullable=False),
        sa.Column("executor_id", sa.LargeBinary(), nullable=False),
        sa.Column("publisher_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("channel_id", sa.LargeBinary(), nullable=False),
        sa.Column("channel_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("bundle_sha256", sa.String(length=64), nullable=False),
        sa.Column("signature_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=31), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("execution_id", name="pk_release_publication_executions"),
        sa.UniqueConstraint("handoff_id", name="uq_release_publication_execution_handoff"),
        sa.ForeignKeyConstraint(["handoff_id"], ["release_publication_handoffs.handoff_id"], name="fk_release_execution_handoff"),
        sa.ForeignKeyConstraint(["executor_id"], ["release_publication_executors.executor_id"], name="fk_release_execution_executor"),
        sa.ForeignKeyConstraint(["publisher_authority_id"], ["release_publisher_authorities.authority_id"], name="fk_release_execution_publisher"),
        sa.ForeignKeyConstraint(["channel_revision_id", "channel_id"], ["release_publication_channel_revisions.revision_id", "release_publication_channel_revisions.channel_id"], name="fk_release_execution_channel_revision"),
        sa.CheckConstraint("status IN ('prepared','outcome_unknown','published','published_reassessment_required')", name="ck_release_publication_execution_status"),
    )
    op.create_table(
        "release_publication_execution_attempts",
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("execution_id", sa.LargeBinary(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("attempt_id", name="pk_release_publication_attempts"),
        sa.UniqueConstraint("execution_id", "attempt_number", name="uq_release_execution_attempt_number"),
        sa.ForeignKeyConstraint(["execution_id"], ["release_publication_executions.execution_id"], name="fk_release_attempt_execution"),
        sa.CheckConstraint("attempt_number>0", name="ck_release_attempt_number_positive"),
        sa.CheckConstraint("status IN ('prepared','write_started','outcome_unknown','reconciled')", name="ck_release_publication_attempt_status"),
        sa.CheckConstraint("(status IN ('prepared','write_started','outcome_unknown') AND finished_at IS NULL) OR (status='reconciled' AND finished_at IS NOT NULL)", name="ck_release_attempt_finish_state"),
    )
    op.create_table(
        "release_publication_receipt_reconciliations",
        sa.Column("receipt_id", sa.LargeBinary(), nullable=False),
        sa.Column("execution_id", sa.LargeBinary(), nullable=False),
        sa.Column("attempt_id", sa.LargeBinary(), nullable=False),
        sa.Column("external_artifact_id", sa.LargeBinary(), nullable=False),
        sa.Column("provider_revision", sa.LargeBinary(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=31), nullable=False),
        sa.PrimaryKeyConstraint("receipt_id", name="pk_release_receipt_reconciliations"),
        sa.UniqueConstraint("execution_id", name="uq_release_receipt_execution"),
        sa.UniqueConstraint("attempt_id", name="uq_release_receipt_attempt"),
        sa.ForeignKeyConstraint(["receipt_id"], ["release_publication_receipts.receipt_id"], name="fk_release_reconciliation_receipt"),
        sa.ForeignKeyConstraint(["execution_id"], ["release_publication_executions.execution_id"], name="fk_release_reconciliation_execution"),
        sa.ForeignKeyConstraint(["attempt_id"], ["release_publication_execution_attempts.attempt_id"], name="fk_release_reconciliation_attempt"),
        sa.CheckConstraint("length(external_artifact_id)>0", name="ck_release_external_artifact_present"),
        sa.CheckConstraint("length(provider_revision)>0", name="ck_release_provider_revision_present"),
        sa.CheckConstraint("status IN ('published','published_reassessment_required')", name="ck_release_reconciliation_status"),
    )
    op.create_table(
        "release_publication_execution_reassessments",
        sa.Column("execution_id", sa.LargeBinary(), nullable=False),
        sa.Column("reassessment_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("execution_id", "reassessment_id", name="pk_release_execution_reassessments"),
        sa.ForeignKeyConstraint(["execution_id"], ["release_publication_executions.execution_id"], name="fk_release_execution_reassessment_execution"),
        sa.ForeignKeyConstraint(["reassessment_id"], ["release_publication_reassessments.reassessment_id"], name="fk_release_execution_reassessment_reassessment"),
    )


def downgrade() -> None:
    op.drop_table("release_publication_execution_reassessments")
    op.drop_table("release_publication_receipt_reconciliations")
    op.drop_table("release_publication_execution_attempts")
    op.drop_table("release_publication_executions")
    op.drop_table("release_publication_executors")
