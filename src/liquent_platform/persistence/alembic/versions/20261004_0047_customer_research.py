"""Add private immutable research uploads and explicitly classified feedback.

Revision ID: 20261004_0047
Revises: 20260916_0046
"""

from alembic import op
import sqlalchemy as sa

revision = "20261004_0047"
down_revision = "20260916_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_research_requests",
        sa.Column("request_id", sa.LargeBinary(), primary_key=True),
        sa.Column("owner_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("input_binding", sa.String(71), nullable=False),
        sa.Column("dataset_fingerprint", sa.String(71), nullable=False),
        sa.Column("configuration_json", sa.Text(), nullable=False),
        sa.Column("dataset_csv", sa.LargeBinary(), nullable=False),
        sa.Column("data_rights", sa.Boolean(), nullable=False),
        sa.Column("execution_approved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id", "workspace_id"],
                                ["workspace_memberships.user_id", "workspace_memberships.workspace_id"]),
        sa.UniqueConstraint("owner_user_id", "workspace_id", "input_binding",
                            name="uq_customer_research_bound_owner"),
        sa.CheckConstraint("length(input_binding)=71", name="ck_customer_research_binding"),
        sa.CheckConstraint("length(dataset_fingerprint)=71", name="ck_customer_research_dataset"),
        sa.CheckConstraint("length(dataset_csv)>0 AND length(dataset_csv)<=5242880",
                           name="ck_customer_research_dataset_size"),
        sa.CheckConstraint("data_rights AND execution_approved", name="ck_customer_research_approval"),
    )
    op.create_table(
        "customer_research_feedback",
        sa.Column("feedback_id", sa.LargeBinary(), primary_key=True),
        sa.Column("owner_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("workspace_id", sa.LargeBinary(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("feedback_json", sa.Text(), nullable=False),
        sa.Column("evidence_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id", "workspace_id"],
                                ["workspace_memberships.user_id", "workspace_memberships.workspace_id"]),
        sa.CheckConstraint("evidence_type='self_report_not_purchase'", name="ck_customer_feedback_evidence"),
    )
    op.create_index("ix_customer_feedback_namespace", "customer_research_feedback",
                    ["workspace_id", "synthetic", "created_at"])


def downgrade() -> None:
    # A schema rollback must not silently erase customer uploads or feedback.
    raise RuntimeError("Customer research data requires an explicit preservation plan before downgrade")
