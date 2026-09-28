"""Add immutable release-registry bootstrap decisions.

Revision ID: 20260817_0018
Revises: 20260817_0017
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0018"
down_revision: str | Sequence[str] | None = "20260817_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_registry_bootstraps",
        sa.Column("bootstrap_id", sa.LargeBinary(), nullable=False),
        sa.Column("lifecycle_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("signer_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.LargeBinary(), nullable=False),
        sa.Column("registry_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("policy_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("bootstrap_id", name="pk_release_registry_bootstraps"),
        sa.ForeignKeyConstraint(
            ["lifecycle_authority_id"],
            ["release_registry_lifecycle_authorities.authority_id"],
            name="fk_release_bootstrap_lifecycle_authority",
        ),
        sa.ForeignKeyConstraint(
            ["signer_authority_id"], ["release_signer_authorities.authority_id"],
            name="fk_release_bootstrap_signer_authority",
        ),
        sa.ForeignKeyConstraint(
            ["key_id", "signer_authority_id"],
            ["release_signing_keys.key_id", "release_signing_keys.signer_authority_id"],
            name="fk_release_bootstrap_key_authority",
        ),
        sa.ForeignKeyConstraint(
            ["registry_revision_id", "policy_revision_id"],
            [
                "release_registry_set_revisions.revision_id",
                "release_registry_set_revisions.policy_revision_id",
            ],
            name="fk_release_bootstrap_revision_policy",
        ),
        sa.CheckConstraint(
            "length(bootstrap_id) > 0", name="ck_release_bootstrap_present"
        ),
    )


def downgrade() -> None:
    op.drop_table("release_registry_bootstraps")
