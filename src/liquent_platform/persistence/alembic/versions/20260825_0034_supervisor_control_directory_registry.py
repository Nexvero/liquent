"""Add persistent private supervisor control-directory registry.

Revision ID: 20260825_0034
Revises: 20260825_0033
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260825_0034"
down_revision: str | Sequence[str] | None = "20260825_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manifest_handoff_supervisor_control_directories",
        sa.Column("directory_id", sa.LargeBinary(), nullable=False),
        sa.Column("handle_id", sa.LargeBinary(), nullable=False),
        sa.Column("leaf", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=8), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("directory_id", name="pk_manifest_handoff_supervisor_control_directories"),
        sa.UniqueConstraint("handle_id", name="uq_manifest_handoff_supervisor_control_directory_handle"),
        sa.UniqueConstraint("leaf", name="uq_manifest_handoff_supervisor_control_directory_leaf"),
        sa.ForeignKeyConstraint(["handle_id"], ["manifest_handoff_supervisor_journal_jobs.handle_id"],
            name="fk_manifest_handoff_supervisor_control_directory_job"),
        sa.CheckConstraint("length(directory_id)>0",
            name="ck_manifest_handoff_supervisor_control_directory_id"),
        sa.CheckConstraint("length(leaf)=64 AND leaf=lower(leaf)",
            name="ck_manifest_handoff_supervisor_control_directory_leaf"),
        sa.CheckConstraint("state IN ('reserved','active','retired')",
            name="ck_manifest_handoff_supervisor_control_directory_state"),
        sa.CheckConstraint(
            "(state='reserved' AND activated_at IS NULL AND retired_at IS NULL) OR "
            "(state='active' AND activated_at IS NOT NULL AND retired_at IS NULL) OR "
            "(state='retired' AND activated_at IS NOT NULL AND retired_at IS NOT NULL)",
            name="ck_manifest_handoff_supervisor_control_directory_state_times"),
        sa.CheckConstraint("activated_at IS NULL OR activated_at>=reserved_at",
            name="ck_mh_supervisor_control_directory_activation_order"),
        sa.CheckConstraint("retired_at IS NULL OR retired_at>=activated_at",
            name="ck_mh_supervisor_control_directory_retirement_order"),
    )


def downgrade() -> None:
    op.drop_table("manifest_handoff_supervisor_control_directories")
