"""Add immutable authorized onboarding decisions.

Revision ID: 20260812_0004
Revises: 20260812_0003
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0004"
down_revision: str | Sequence[str] | None = "20260812_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "authorized_onboarding_decisions",
        sa.Column("decision_id", sa.LargeBinary(), nullable=False),
        sa.Column("provisioning_request", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_workspace_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("decision_id", name="pk_onboarding_decisions"),
        sa.UniqueConstraint(
            "provisioning_request", name="uq_onboarding_decisions_request"
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"], name="fk_decision_actor"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"], name="fk_decision_target"
        ),
        sa.ForeignKeyConstraint(
            ["target_workspace_id"],
            ["identity_workspaces.workspace_id"],
            name="fk_decision_workspace",
        ),
        sa.CheckConstraint(
            "length(decision_id) > 0", name="ck_onboarding_decision_id_present"
        ),
        sa.CheckConstraint(
            "length(provisioning_request) > 0",
            name="ck_onboarding_decision_request_present",
        ),
    )


def downgrade() -> None:
    op.drop_table("authorized_onboarding_decisions")
