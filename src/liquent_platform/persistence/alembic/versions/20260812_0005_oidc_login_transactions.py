"""Add persistent single-use OIDC login transactions.

Revision ID: 20260812_0005
Revises: 20260812_0004
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0005"
down_revision: str | Sequence[str] | None = "20260812_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oidc_login_transactions",
        sa.Column("state", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=7), nullable=False),
        sa.Column("expected_issuer", sa.LargeBinary(), nullable=True),
        sa.Column("expected_nonce", sa.LargeBinary(), nullable=True),
        sa.Column("code_verifier", sa.LargeBinary(), nullable=True),
        sa.Column("redirect_uri", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admission_id", sa.LargeBinary(), nullable=True),
        sa.Column("return_path", sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint("state", name="pk_oidc_login_transactions"),
        sa.CheckConstraint("length(state) > 0", name="ck_oidc_login_state_present"),
        sa.CheckConstraint(
            "status IN ('pending', 'used')", name="ck_oidc_login_status"
        ),
        sa.CheckConstraint(
            "(status='pending' AND expected_issuer IS NOT NULL"
            " AND expected_nonce IS NOT NULL AND code_verifier IS NOT NULL"
            " AND redirect_uri IS NOT NULL AND created_at IS NOT NULL"
            " AND expires_at IS NOT NULL) OR (status='used'"
            " AND expected_issuer IS NULL AND expected_nonce IS NULL"
            " AND code_verifier IS NULL AND redirect_uri IS NULL"
            " AND created_at IS NULL AND expires_at IS NULL"
            " AND admission_id IS NULL AND return_path IS NULL)",
            name="ck_oidc_login_pending_or_secret_free_used",
        ),
    )


def downgrade() -> None:
    op.drop_table("oidc_login_transactions")
