"""Add durable supervisor cleanup retention operation bindings.

Revision ID: 20260826_0041
Revises: 20260826_0040
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0041"
down_revision: str | Sequence[str] | None = "20260826_0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OPERATIONS = "manifest_handoff_supervisor_cleanup_retention_operations"
_DECISIONS = "manifest_handoff_supervisor_control_cleanup_decisions"


def upgrade() -> None:
    op.create_table(
        _OPERATIONS,
        sa.Column("operation_id", sa.LargeBinary(), nullable=False),
        sa.Column("directory_id", sa.LargeBinary(), nullable=False),
        sa.Column("decision_id", sa.LargeBinary(), nullable=False),
        sa.Column("policy_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("data_class", sa.String(length=32), nullable=False),
        sa.Column("disposition", sa.String(length=8), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "operation_id",
            name="pk_mh_supervisor_cleanup_retention_operations",
        ),
        sa.UniqueConstraint(
            "operation_id", "directory_id",
            name="uq_mh_supervisor_cleanup_retention_operation_binding",
        ),
        sa.UniqueConstraint(
            "decision_id",
            name="uq_mh_supervisor_cleanup_retention_operation_decision",
        ),
        sa.ForeignKeyConstraint(
            ["decision_id", "directory_id"],
            [f"{_DECISIONS}.decision_id", f"{_DECISIONS}.directory_id"],
            name="fk_mh_supervisor_cleanup_retention_operation_decision",
        ),
        sa.CheckConstraint(
            "length(operation_id)>0",
            name="ck_mh_supervisor_cleanup_retention_operation_id",
        ),
        sa.CheckConstraint(
            "length(policy_revision_id)>0",
            name="ck_mh_supervisor_cleanup_retention_policy_revision",
        ),
        sa.CheckConstraint(
            "data_class='supervisor_control_directory'",
            name="ck_mh_supervisor_cleanup_retention_data_class",
        ),
        sa.CheckConstraint(
            "disposition IN ('retain','eligible')",
            name="ck_mh_supervisor_cleanup_retention_disposition",
        ),
        sa.CheckConstraint(
            "bound_at>=evaluated_at",
            name="ck_mh_supervisor_cleanup_retention_bound_order",
        ),
    )


def downgrade() -> None:
    op.drop_table(_OPERATIONS)
