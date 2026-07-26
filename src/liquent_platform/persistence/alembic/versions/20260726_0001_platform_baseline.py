"""Establish the Liquent platform migration baseline.

Revision ID: 20260726_0001
Revises: None
"""

from typing import Sequence


revision: str = "20260726_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Business tables begin with their owning vertical workflow. Alembic's
    # version table is the only state introduced by this foundation revision.
    pass


def downgrade() -> None:
    pass
