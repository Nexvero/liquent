"""Add the historical singleton decision for initial identity bootstrap.

Revision ID: 20260811_0004
Revises: 20260811_0003
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260811_0004"
down_revision: str | Sequence[str] | None = "20260811_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity_authority_bootstrap_decisions",
        sa.Column("singleton_key", sa.SmallInteger(), nullable=False),
        sa.Column("admission_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "singleton_key", name="pk_identity_authority_bootstrap_decisions"
        ),
        sa.UniqueConstraint(
            "admission_id", name="uq_identity_authority_bootstrap_admission"
        ),
        sa.ForeignKeyConstraint(
            ["admission_id"],
            ["identity_admissions.admission_id"],
            name="fk_identity_authority_bootstrap_admission",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "singleton_key = 1", name="ck_identity_authority_bootstrap_singleton"
        ),
    )


def downgrade() -> None:
    op.drop_table("identity_authority_bootstrap_decisions")
