"""Add the persistent active OIDC client configuration singleton.

Revision ID: 20260812_0007
Revises: 20260812_0006
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0007"
down_revision: str | Sequence[str] | None = "20260812_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oidc_client_configuration",
        sa.Column("singleton_key", sa.SmallInteger(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("issuer", sa.LargeBinary(), nullable=False),
        sa.Column("authorization_endpoint", sa.LargeBinary(), nullable=False),
        sa.Column("client_id", sa.LargeBinary(), nullable=False),
        sa.Column("redirect_uri", sa.LargeBinary(), nullable=False),
        sa.Column("scopes", sa.LargeBinary(), nullable=False),
        sa.Column("token_endpoint", sa.LargeBinary(), nullable=False),
        sa.Column("jwks_uri", sa.LargeBinary(), nullable=False),
        sa.Column("allowed_signing_algorithms", sa.LargeBinary(), nullable=False),
        sa.Column("clock_skew_microseconds", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("singleton_key", name="pk_oidc_client_configuration"),
        sa.CheckConstraint(
            "singleton_key = 1", name="ck_oidc_client_configuration_singleton"
        ),
        sa.CheckConstraint(
            "clock_skew_microseconds >= 0 AND clock_skew_microseconds <= 300000000",
            name="ck_oidc_client_configuration_clock_skew",
        ),
    )


def downgrade() -> None:
    op.drop_table("oidc_client_configuration")
