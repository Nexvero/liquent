"""Add immutable publication-executor registration decisions.

Revision ID: 20260819_0025
Revises: 20260819_0024
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260819_0025"
down_revision: str | Sequence[str] | None = "20260819_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_publication_executor_registrations",
        sa.Column("registration_id", sa.LargeBinary(), nullable=False),
        sa.Column("executor_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "registration_id", name="pk_release_publication_executor_registrations"
        ),
        sa.UniqueConstraint(
            "executor_id", name="uq_release_publication_executor_registration_executor"
        ),
        sa.ForeignKeyConstraint(
            ["executor_id"],
            ["release_publication_executors.executor_id"],
            name="fk_release_publication_executor_registration_executor",
        ),
        sa.CheckConstraint(
            "length(registration_id)>0",
            name="ck_release_publication_executor_registration_present",
        ),
    )


def downgrade() -> None:
    op.drop_table("release_publication_executor_registrations")
