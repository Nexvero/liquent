"""Bind active OIDC configuration and pending logins to trust revisions.

Revision ID: 20260812_0010
Revises: 20260812_0009
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0010"
down_revision: str | Sequence[str] | None = "20260812_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("oidc_client_configuration") as batch:
        batch.add_column(sa.Column("revision_id", sa.LargeBinary(), nullable=True))
        batch.create_foreign_key(
            "fk_active_oidc_trust_revision",
            "oidc_trust_revisions",
            ["revision_id"],
            ["revision_id"],
        )
    with op.batch_alter_table("oidc_login_transactions") as batch:
        batch.add_column(
            sa.Column("expected_trust_revision", sa.LargeBinary(), nullable=True)
        )
        batch.create_foreign_key(
            "fk_login_expected_trust_revision",
            "oidc_trust_revisions",
            ["expected_trust_revision"],
            ["revision_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("oidc_login_transactions") as batch:
        batch.drop_constraint(
            "fk_login_expected_trust_revision", type_="foreignkey"
        )
        batch.drop_column("expected_trust_revision")
    with op.batch_alter_table("oidc_client_configuration") as batch:
        batch.drop_constraint("fk_active_oidc_trust_revision", type_="foreignkey")
        batch.drop_column("revision_id")
