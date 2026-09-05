"""Add terminal execution outcomes for the bounded second attempt.

Revision ID: 20260819_0024
Revises: 20260818_0023
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260819_0024"
down_revision: str | Sequence[str] | None = "20260818_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD = (
    "status IN ('prepared','outcome_unknown','published',"
    "'published_reassessment_required')"
)
_NEW = (
    "status IN ('prepared','outcome_unknown','published',"
    "'published_reassessment_required','not_published','publication_conflict')"
)


def upgrade() -> None:
    with op.batch_alter_table("release_publication_executions") as batch:
        batch.drop_constraint("ck_release_publication_execution_status", type_="check")
        batch.create_check_constraint("ck_release_publication_execution_status", _NEW)


def downgrade() -> None:
    with op.batch_alter_table("release_publication_executions") as batch:
        batch.drop_constraint("ck_release_publication_execution_status", type_="check")
        batch.create_check_constraint("ck_release_publication_execution_status", _OLD)
