"""Add immutable release-key activation decisions.

Revision ID: 20260817_0019
Revises: 20260817_0018
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0019"
down_revision: str | Sequence[str] | None = "20260817_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_key_activations",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_lifecycle_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.LargeBinary(), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("challenge_sha256", sa.String(length=64), nullable=False),
        sa.Column("proof_sha256", sa.String(length=64), nullable=False),
        sa.Column("approval_sha256", sa.String(length=64), nullable=False),
        sa.Column("reviewer_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name="pk_release_key_activations"),
        sa.ForeignKeyConstraint(
            ["change_id"], ["release_registry_lifecycle_changes.change_id"],
            name="fk_release_activation_change",
        ),
        sa.ForeignKeyConstraint(
            ["actor_lifecycle_authority_id"],
            ["release_registry_lifecycle_authorities.authority_id"],
            name="fk_release_activation_actor",
        ),
        sa.ForeignKeyConstraint(
            ["key_id"], ["release_signing_keys.key_id"],
            name="fk_release_activation_key",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], ["release_registry_set_revisions.revision_id"],
            name="fk_release_activation_expected",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id"], ["release_registry_set_revisions.revision_id"],
            name="fk_release_activation_resulting",
        ),
        sa.CheckConstraint("length(reviewer_id)>0", name="ck_release_activation_reviewer"),
    )


def downgrade() -> None:
    op.drop_table("release_key_activations")
