"""Add the pre-provisioned staging Research-index fixture registry.

Revision ID: 20260915_0043
Revises: 20260826_0042
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_0043"
down_revision: str | Sequence[str] | None = "20260826_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staging_research_index_fixtures",
        sa.Column("fixture_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("active_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("fixture_id", name="pk_staging_research_index_fixtures"),
        sa.UniqueConstraint(
            "active_revision_id", name="uq_staging_research_index_fixture_revision"
        ),
        sa.UniqueConstraint(
            "target_user_id", "workspace_id",
            name="uq_staging_research_index_fixture_target",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["identity_users.user_id"],
            name="fk_staging_research_index_fixture_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["identity_users.user_id"],
            name="fk_staging_research_index_fixture_target",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["identity_workspaces.workspace_id"],
            name="fk_staging_research_index_fixture_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["active_revision_id"], ["workspace_membership_revisions.revision_id"],
            name="fk_staging_research_index_fixture_revision",
        ),
        sa.CheckConstraint(
            "length(fixture_id)>0", name="ck_staging_research_index_fixture_id"
        ),
    )


def downgrade() -> None:
    op.drop_table("staging_research_index_fixtures")
