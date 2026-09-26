"""Add non-authorizing staging promotion evidence bindings.

Revision ID: 20260916_0045
Revises: 20260916_0044
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260916_0045"
down_revision: str | Sequence[str] | None = "20260916_0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staging_research_index_promotion_evidence",
        sa.Column("evidence_digest", sa.String(length=71), nullable=False),
        sa.Column("candidate_digest", sa.String(length=71), nullable=False),
        sa.Column("staging_origin", sa.String(length=512), nullable=False),
        sa.Column("observed_at", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint(
            "evidence_digest", name="pk_staging_research_index_promotion_evidence"
        ),
        sa.CheckConstraint(
            "length(evidence_digest)=71",
            name="ck_staging_promotion_evidence_digest",
        ),
        sa.CheckConstraint(
            "length(candidate_digest)=71",
            name="ck_staging_promotion_candidate_digest",
        ),
        sa.CheckConstraint(
            "length(staging_origin)>0", name="ck_staging_promotion_origin"
        ),
        sa.CheckConstraint(
            "length(observed_at)>0", name="ck_staging_promotion_observed_at"
        ),
    )


def downgrade() -> None:
    op.drop_table("staging_research_index_promotion_evidence")
