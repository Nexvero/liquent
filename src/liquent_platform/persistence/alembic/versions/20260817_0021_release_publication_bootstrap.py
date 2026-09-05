"""Add immutable publication control-plane bootstrap decisions.

Revision ID: 20260817_0021
Revises: 20260817_0020
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0021"
down_revision: str | Sequence[str] | None = "20260817_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_publication_bootstraps",
        sa.Column("bootstrap_id", sa.LargeBinary(), nullable=False),
        sa.Column("publisher_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("channel_id", sa.LargeBinary(), nullable=False),
        sa.Column("channel_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("package_name", sa.String(length=64), nullable=False),
        sa.Column("provider_kind", sa.String(length=32), nullable=False),
        sa.Column("target_name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("bootstrap_id", name="pk_release_publication_bootstraps"),
        sa.ForeignKeyConstraint(["publisher_authority_id"], ["release_publisher_authorities.authority_id"], name="fk_release_publication_bootstrap_publisher"),
        sa.ForeignKeyConstraint(["channel_revision_id", "channel_id"], ["release_publication_channel_revisions.revision_id", "release_publication_channel_revisions.channel_id"], name="fk_release_publication_bootstrap_channel_revision"),
        sa.CheckConstraint("length(bootstrap_id)>0", name="ck_release_publication_bootstrap_present"),
    )


def downgrade() -> None:
    op.drop_table("release_publication_bootstraps")
