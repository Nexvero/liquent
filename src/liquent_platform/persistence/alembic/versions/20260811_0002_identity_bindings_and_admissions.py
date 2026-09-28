"""Add the external-identity binding and identity-admission tables.

Revision ID: 20260811_0002
Revises: 20260726_0001

Every identity-bearing key column is stored as raw bytes. These values decide
uniqueness and equality, and text equality in PostgreSQL depends on the
database's collation: a non-deterministic collation would treat distinct values
as identical. Bytes keep the contract independent of that configuration and are
portable, compiling to BYTEA and BLOB. No seed data, no user or workspace
foreign key (neither table exists), and no created_at.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260811_0002"
down_revision: str | Sequence[str] | None = "20260726_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_identity_bindings",
        sa.Column("issuer", sa.LargeBinary(), nullable=False),
        sa.Column("subject", sa.LargeBinary(), nullable=False),
        sa.Column("user_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "issuer", "subject", name="pk_external_identity_bindings"
        ),
        # One internal user carries at most one external identity, exactly as
        # the in-memory contract already refuses a second binding.
        sa.UniqueConstraint("user_id", name="uq_external_identity_bindings_user_id"),
        sa.CheckConstraint(
            "length(issuer) > 0", name="ck_external_identity_bindings_issuer_present"
        ),
        sa.CheckConstraint(
            "length(subject) > 0", name="ck_external_identity_bindings_subject_present"
        ),
        sa.CheckConstraint(
            "length(user_id) > 0", name="ck_external_identity_bindings_user_present"
        ),
    )
    op.create_table(
        "identity_admissions",
        sa.Column("admission_id", sa.LargeBinary(), nullable=False),
        sa.Column("provisioning_request", sa.LargeBinary(), nullable=False),
        sa.Column("target_user_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_workspace_id", sa.LargeBinary(), nullable=False),
        # The originally requested lifetime, lossless in whole microseconds, so
        # a later provisioning retry can compare inputs without a created_at.
        sa.Column("lifetime_microseconds", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bound_issuer", sa.LargeBinary(), nullable=True),
        sa.Column("bound_subject", sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint("admission_id", name="pk_identity_admissions"),
        # One admission per provisioning request: the uniqueness that makes a
        # later retry resolvable rather than duplicating an admission.
        sa.UniqueConstraint(
            "provisioning_request",
            name="uq_identity_admissions_provisioning_request",
        ),
        sa.CheckConstraint(
            "length(admission_id) > 0", name="ck_identity_admissions_id_present"
        ),
        sa.CheckConstraint(
            "length(provisioning_request) > 0",
            name="ck_identity_admissions_request_present",
        ),
        sa.CheckConstraint(
            "length(target_user_id) > 0",
            name="ck_identity_admissions_target_user_present",
        ),
        sa.CheckConstraint(
            "length(target_workspace_id) > 0",
            name="ck_identity_admissions_target_workspace_present",
        ),
        sa.CheckConstraint(
            "lifetime_microseconds > 0",
            name="ck_identity_admissions_lifetime_positive",
        ),
        # Consumption is one indivisible fact: an admission is either open or
        # bound to exactly one identity at one instant, never half of that.
        sa.CheckConstraint(
            "(consumed_at IS NULL AND bound_issuer IS NULL AND bound_subject IS NULL)"
            " OR (consumed_at IS NOT NULL AND bound_issuer IS NOT NULL"
            " AND bound_subject IS NOT NULL)",
            name="ck_identity_admissions_consumption_group",
        ),
        sa.CheckConstraint(
            "bound_issuer IS NULL OR length(bound_issuer) > 0",
            name="ck_identity_admissions_bound_issuer_present",
        ),
        sa.CheckConstraint(
            "bound_subject IS NULL OR length(bound_subject) > 0",
            name="ck_identity_admissions_bound_subject_present",
        ),
    )


def downgrade() -> None:
    op.drop_table("identity_admissions")
    op.drop_table("external_identity_bindings")
