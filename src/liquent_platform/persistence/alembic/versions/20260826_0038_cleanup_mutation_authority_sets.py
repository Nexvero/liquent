"""Add cleanup mutation authority-set foundations.

Revision ID: 20260826_0038
Revises: 20260826_0037
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0038"
down_revision: str | Sequence[str] | None = "20260826_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _authority_inventory(kind: str, prefix: str) -> None:
    root = f"mh_supervisor_cleanup_{kind}_authority"
    sets = f"{root}_sets"
    members = f"{root}_members"

    op.create_table(
        sets,
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name=f"pk_{prefix}_sets"),
        sa.UniqueConstraint(
            "revision_id", "scope_id", name=f"uq_{prefix}_set_binding"
        ),
        sa.UniqueConstraint(
            "scope_id", "sequence_number", name=f"uq_{prefix}_set_sequence"
        ),
        sa.ForeignKeyConstraint(
            ["scope_id"], ["manifest_handoff_registry_scopes.scope_id"],
            name=f"fk_{prefix}_set_scope",
        ),
        sa.CheckConstraint("length(revision_id)>0", name=f"ck_{prefix}_set_id"),
        sa.CheckConstraint("sequence_number>0", name=f"ck_{prefix}_set_sequence"),
    )
    op.create_table(
        members,
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "user_id", name=f"pk_{prefix}_members"
        ),
        sa.UniqueConstraint(
            "revision_id", "scope_id", "user_id",
            name=f"uq_{prefix}_member_binding",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "scope_id"],
            [f"{sets}.revision_id", f"{sets}.scope_id"],
            name=f"fk_{prefix}_member_set",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity_users.user_id"],
            name=f"fk_{prefix}_member_user",
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive')", name=f"ck_{prefix}_member_status"
        ),
    )
    op.create_table(
        f"{root}_current",
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("scope_id", name=f"pk_{prefix}_current"),
        sa.UniqueConstraint("revision_id", name=f"uq_{prefix}_current_revision"),
        sa.ForeignKeyConstraint(
            ["revision_id", "scope_id"],
            [f"{sets}.revision_id", f"{sets}.scope_id"],
            name=f"fk_{prefix}_current_set",
        ),
    )
    op.create_table(
        f"{root}_bootstraps",
        sa.Column("bootstrap_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("result_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("bootstrapped_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("bootstrap_id", name=f"pk_{prefix}_bootstraps"),
        sa.UniqueConstraint("scope_id", name=f"uq_{prefix}_bootstrap_scope"),
        sa.UniqueConstraint(
            "result_revision_id", name=f"uq_{prefix}_bootstrap_result"
        ),
        sa.ForeignKeyConstraint(
            ["result_revision_id", "scope_id", "target_user_id"],
            [f"{members}.revision_id", f"{members}.scope_id", f"{members}.user_id"],
            name=f"fk_{prefix}_bootstrap_member",
        ),
        sa.CheckConstraint(
            "length(bootstrap_id)>0", name=f"ck_{prefix}_bootstrap_id"
        ),
    )
    op.create_table(
        f"{root}_changes",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("result_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("intent", sa.String(length=10), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name=f"pk_{prefix}_changes"),
        sa.UniqueConstraint(
            "result_revision_id", name=f"uq_{prefix}_change_result"
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id", "scope_id"],
            [f"{sets}.revision_id", f"{sets}.scope_id"],
            name=f"fk_{prefix}_change_expected",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id", "scope_id", "actor_user_id"],
            [f"{members}.revision_id", f"{members}.scope_id", f"{members}.user_id"],
            name=f"fk_{prefix}_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["result_revision_id", "scope_id", "target_user_id"],
            [f"{members}.revision_id", f"{members}.scope_id", f"{members}.user_id"],
            name=f"fk_{prefix}_change_target",
        ),
        sa.CheckConstraint("length(change_id)>0", name=f"ck_{prefix}_change_id"),
        sa.CheckConstraint(
            "intent IN ('grant','deactivate','reactivate')",
            name=f"ck_{prefix}_change_intent",
        ),
        sa.CheckConstraint(
            "expected_revision_id<>result_revision_id",
            name=f"ck_{prefix}_change_revisions",
        ),
    )
    op.create_table(
        f"{root}_recoveries",
        sa.Column("recovery_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("scope_id", sa.LargeBinary(), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("result_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("recovery_id", name=f"pk_{prefix}_recoveries"),
        sa.UniqueConstraint(
            "result_revision_id", name=f"uq_{prefix}_recovery_result"
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id", "scope_id", "target_user_id"],
            [f"{members}.revision_id", f"{members}.scope_id", f"{members}.user_id"],
            name=f"fk_{prefix}_recovery_history",
        ),
        sa.ForeignKeyConstraint(
            ["result_revision_id", "scope_id", "target_user_id"],
            [f"{members}.revision_id", f"{members}.scope_id", f"{members}.user_id"],
            name=f"fk_{prefix}_recovery_result",
        ),
        sa.CheckConstraint("length(recovery_id)>0", name=f"ck_{prefix}_recovery_id"),
        sa.CheckConstraint(
            "expected_revision_id<>result_revision_id",
            name=f"ck_{prefix}_recovery_revisions",
        ),
    )


def upgrade() -> None:
    _authority_inventory("management", "mhscma")
    _authority_inventory("hold", "mhsch")
    _authority_inventory("recovery", "mhscr")
    _authority_inventory("reference", "mhscf")


def downgrade() -> None:
    for kind in ("reference", "recovery", "hold", "management"):
        root = f"mh_supervisor_cleanup_{kind}_authority"
        op.drop_table(f"{root}_recoveries")
        op.drop_table(f"{root}_changes")
        op.drop_table(f"{root}_bootstraps")
        op.drop_table(f"{root}_current")
        op.drop_table(f"{root}_members")
        op.drop_table(f"{root}_sets")
