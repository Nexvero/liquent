"""Add crash-safe staging promotion attempt journal.

Revision ID: 20260916_0046
Revises: 20260916_0045
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260916_0046"
down_revision: str | Sequence[str] | None = "20260916_0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staging_research_index_promotion_attempts",
        sa.Column("operation_id", sa.String(length=256), nullable=False),
        sa.Column("actor_user_id", sa.String(length=255), nullable=False),
        sa.Column("evidence_digest", sa.String(length=71), nullable=False),
        sa.Column("candidate_digest", sa.String(length=71), nullable=False),
        sa.Column("staging_origin", sa.String(length=512), nullable=False),
        sa.Column("target_environment", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("operation_id", name="pk_staging_promotion_attempts"),
        sa.CheckConstraint("length(operation_id)>0", name="ck_staging_promotion_operation"),
        sa.CheckConstraint("length(actor_user_id)>0", name="ck_staging_promotion_actor"),
        sa.CheckConstraint("length(evidence_digest)=71", name="ck_staging_promotion_attempt_evidence"),
        sa.CheckConstraint("length(candidate_digest)=71", name="ck_staging_promotion_attempt_candidate"),
        sa.CheckConstraint("length(staging_origin)>0", name="ck_staging_promotion_attempt_origin"),
        sa.CheckConstraint("length(target_environment)>0", name="ck_staging_promotion_attempt_target"),
        sa.CheckConstraint("length(created_at)>0", name="ck_staging_promotion_attempt_created"),
    )
    op.create_table(
        "staging_research_index_promotion_attempt_events",
        sa.Column("operation_id", sa.String(length=256), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("provider_receipt_id", sa.String(length=256), nullable=True),
        sa.Column("observed_at", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["staging_research_index_promotion_attempts.operation_id"],
            name="fk_staging_promotion_event_attempt",
        ),
        sa.PrimaryKeyConstraint(
            "operation_id", "sequence", name="pk_staging_promotion_attempt_events"
        ),
        sa.CheckConstraint("sequence>=1", name="ck_staging_promotion_event_sequence"),
        sa.CheckConstraint(
            "state IN ('prepared','write_started','effect_unknown','committed')",
            name="ck_staging_promotion_event_state",
        ),
        sa.CheckConstraint(
            "(state='committed' AND provider_receipt_id IS NOT NULL) OR "
            "(state!='committed' AND provider_receipt_id IS NULL)",
            name="ck_staging_promotion_event_receipt",
        ),
        sa.CheckConstraint("length(observed_at)>0", name="ck_staging_promotion_event_observed"),
    )


def downgrade() -> None:
    op.drop_table("staging_research_index_promotion_attempt_events")
    op.drop_table("staging_research_index_promotion_attempts")
