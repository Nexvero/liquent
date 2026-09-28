"""Add immutable authorized OIDC trust-change decisions.

Revision ID: 20260812_0011
Revises: 20260812_0010
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0011"
down_revision: str | Sequence[str] | None = "20260812_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "authorized_oidc_trust_changes",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=True),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint("change_id", name="pk_oidc_trust_changes"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_oidc_trust_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], ["oidc_trust_revisions.revision_id"],
            name="fk_oidc_trust_change_expected_revision",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id"], ["oidc_trust_revisions.revision_id"],
            name="fk_oidc_trust_change_resulting_revision",
        ),
        sa.CheckConstraint(
            "length(change_id) > 0", name="ck_oidc_trust_change_id_present"
        ),
        sa.CheckConstraint(
            "kind IN ('activate','rotate','deactivate')",
            name="ck_oidc_trust_change_kind",
        ),
        sa.CheckConstraint(
            "(kind = 'activate' AND expected_revision_id IS NULL"
            " AND resulting_revision_id IS NOT NULL) OR"
            " (kind = 'rotate' AND expected_revision_id IS NOT NULL"
            " AND resulting_revision_id IS NOT NULL) OR"
            " (kind = 'deactivate' AND expected_revision_id IS NOT NULL"
            " AND resulting_revision_id IS NULL)",
            name="ck_oidc_trust_change_shape",
        ),
    )


def downgrade() -> None:
    op.drop_table("authorized_oidc_trust_changes")
