"""Add OIDC-trust authority and immutable revision foundation.

Revision ID: 20260812_0009
Revises: 20260812_0008
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0009"
down_revision: str | Sequence[str] | None = "20260812_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oidc_trust_management_authorities",
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name="pk_oidc_trust_authorities"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"], name="fk_oidc_trust_authority_user"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_oidc_trust_authority_status"
        ),
    )
    op.create_table(
        "oidc_trust_revisions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("issuer", sa.LargeBinary(), nullable=False),
        sa.Column("authorization_endpoint", sa.LargeBinary(), nullable=False),
        sa.Column("client_id", sa.LargeBinary(), nullable=False),
        sa.Column("redirect_uri", sa.LargeBinary(), nullable=False),
        sa.Column("scopes", sa.LargeBinary(), nullable=False),
        sa.Column("token_endpoint", sa.LargeBinary(), nullable=False),
        sa.Column("jwks_uri", sa.LargeBinary(), nullable=False),
        sa.Column("allowed_signing_algorithms", sa.LargeBinary(), nullable=False),
        sa.Column("clock_skew_microseconds", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name="pk_oidc_trust_revisions"),
        sa.CheckConstraint(
            "length(revision_id) > 0", name="ck_oidc_trust_revision_id_present"
        ),
        sa.CheckConstraint(
            "clock_skew_microseconds >= 0 AND clock_skew_microseconds <= 300000000",
            name="ck_oidc_trust_revision_clock_skew",
        ),
    )


def downgrade() -> None:
    op.drop_table("oidc_trust_revisions")
    op.drop_table("oidc_trust_management_authorities")
