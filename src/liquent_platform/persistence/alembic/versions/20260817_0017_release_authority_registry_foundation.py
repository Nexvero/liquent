"""Add the empty release-authority registry foundation.

Revision ID: 20260817_0017
Revises: 20260813_0016
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0017"
down_revision: str | Sequence[str] | None = "20260813_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTHORITY_STATUS = "status IN ('active','inactive')"
_KEY_STATUS = "status IN ('active','inactive','expired','revoked')"
_POLICY_STATUS = "policy_status IN ('active','inactive')"
_TARGET = (
    "(target_kind = 'signer' AND target_signer_authority_id IS NOT NULL "
    "AND target_lifecycle_authority_id IS NULL AND target_key_id IS NULL) OR "
    "(target_kind = 'lifecycle' AND target_signer_authority_id IS NULL "
    "AND target_lifecycle_authority_id IS NOT NULL AND target_key_id IS NULL) OR "
    "(target_kind = 'key' AND target_signer_authority_id IS NULL "
    "AND target_lifecycle_authority_id IS NULL AND target_key_id IS NOT NULL)"
)
_INTENT = (
    "(target_kind IN ('signer','lifecycle') "
    "AND intent IN ('grant','deactivate','reactivate')) OR "
    "(target_kind = 'key' AND intent IN "
    "('provision','activate','deactivate','reactivate','expire','revoke'))"
)


def upgrade() -> None:
    op.create_table(
        "release_signer_authorities",
        sa.Column("authority_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("authority_id", name="pk_release_signer_authorities"),
        sa.CheckConstraint(
            "length(authority_id) > 0", name="ck_release_signer_authority_present"
        ),
    )
    op.create_table(
        "release_registry_lifecycle_authorities",
        sa.Column("authority_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint(
            "authority_id", name="pk_release_registry_lifecycle_authorities"
        ),
        sa.CheckConstraint(
            "length(authority_id) > 0",
            name="ck_release_registry_lifecycle_authority_present",
        ),
    )
    op.create_table(
        "release_signing_keys",
        sa.Column("key_id", sa.LargeBinary(), nullable=False),
        sa.Column("signer_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("algorithm", sa.String(length=16), nullable=False),
        sa.Column("namespace", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key_id", name="pk_release_signing_keys"),
        sa.UniqueConstraint(
            "key_id", "signer_authority_id", name="uq_release_key_authority"
        ),
        sa.UniqueConstraint("fingerprint", name="uq_release_key_fingerprint"),
        sa.UniqueConstraint("public_key", name="uq_release_public_key"),
        sa.ForeignKeyConstraint(
            ["signer_authority_id"],
            ["release_signer_authorities.authority_id"],
            name="fk_release_key_signer_authority",
        ),
        sa.CheckConstraint("length(key_id) > 0", name="ck_release_key_id_present"),
        sa.CheckConstraint(
            "algorithm = 'ssh-ed25519'", name="ck_release_key_algorithm"
        ),
        sa.CheckConstraint(
            "namespace = 'liquent-operations-release-v1'",
            name="ck_release_key_namespace",
        ),
        sa.CheckConstraint(
            "length(fingerprint) > 0", name="ck_release_key_fingerprint_present"
        ),
        sa.CheckConstraint(
            "length(public_key) > 0", name="ck_release_public_key_present"
        ),
    )
    op.create_table(
        "release_registry_set_revisions",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("policy_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("policy_status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", name="pk_release_registry_revisions"),
        sa.UniqueConstraint(
            "revision_id", "policy_revision_id", name="uq_release_revision_policy"
        ),
        sa.CheckConstraint(
            "length(revision_id) > 0", name="ck_release_registry_revision_present"
        ),
        sa.CheckConstraint(
            "length(policy_revision_id) > 0",
            name="ck_release_policy_revision_present",
        ),
        sa.CheckConstraint(_POLICY_STATUS, name="ck_release_policy_status"),
    )
    op.create_table(
        "release_registry_revision_signers",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "authority_id", name="pk_release_revision_signers"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["release_registry_set_revisions.revision_id"],
            name="fk_release_revision_signer_revision", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["authority_id"], ["release_signer_authorities.authority_id"],
            name="fk_release_revision_signer_authority",
        ),
        sa.CheckConstraint(_AUTHORITY_STATUS, name="ck_release_revision_signer_status"),
    )
    op.create_table(
        "release_registry_revision_lifecycle_authorities",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "authority_id", name="pk_release_revision_lifecycle"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["release_registry_set_revisions.revision_id"],
            name="fk_release_revision_lifecycle_revision", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["authority_id"], ["release_registry_lifecycle_authorities.authority_id"],
            name="fk_release_revision_lifecycle_authority",
        ),
        sa.CheckConstraint(
            _AUTHORITY_STATUS, name="ck_release_revision_lifecycle_status"
        ),
    )
    op.create_table(
        "release_registry_revision_keys",
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.LargeBinary(), nullable=False),
        sa.Column("signer_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint(
            "revision_id", "key_id", name="pk_release_revision_keys"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["release_registry_set_revisions.revision_id"],
            name="fk_release_revision_key_revision", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["key_id", "signer_authority_id"],
            ["release_signing_keys.key_id", "release_signing_keys.signer_authority_id"],
            name="fk_release_revision_key_authority",
        ),
        sa.CheckConstraint(_KEY_STATUS, name="ck_release_revision_key_status"),
    )
    op.create_table(
        "release_registry_current_set",
        sa.Column("singleton_key", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("singleton_key", name="pk_release_registry_current"),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["release_registry_set_revisions.revision_id"],
            name="fk_release_registry_current_revision",
        ),
        sa.CheckConstraint(
            "singleton_key = 1", name="ck_release_registry_current_singleton"
        ),
    )
    op.create_table(
        "release_registry_lifecycle_changes",
        sa.Column("change_id", sa.LargeBinary(), nullable=False),
        sa.Column("actor_lifecycle_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("target_kind", sa.String(length=10), nullable=False),
        sa.Column("target_signer_authority_id", sa.LargeBinary(), nullable=True),
        sa.Column("target_lifecycle_authority_id", sa.LargeBinary(), nullable=True),
        sa.Column("target_key_id", sa.LargeBinary(), nullable=True),
        sa.Column("intent", sa.String(length=10), nullable=False),
        sa.Column("expected_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("resulting_revision_id", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("change_id", name="pk_release_registry_changes"),
        sa.ForeignKeyConstraint(
            ["actor_lifecycle_authority_id"],
            ["release_registry_lifecycle_authorities.authority_id"],
            name="fk_release_change_actor",
        ),
        sa.ForeignKeyConstraint(
            ["target_signer_authority_id"],
            ["release_signer_authorities.authority_id"],
            name="fk_release_change_target_signer",
        ),
        sa.ForeignKeyConstraint(
            ["target_lifecycle_authority_id"],
            ["release_registry_lifecycle_authorities.authority_id"],
            name="fk_release_change_target_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["target_key_id"], ["release_signing_keys.key_id"],
            name="fk_release_change_target_key",
        ),
        sa.ForeignKeyConstraint(
            ["expected_revision_id"], ["release_registry_set_revisions.revision_id"],
            name="fk_release_change_expected_revision",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_revision_id"], ["release_registry_set_revisions.revision_id"],
            name="fk_release_change_resulting_revision",
        ),
        sa.CheckConstraint("length(change_id) > 0", name="ck_release_change_present"),
        sa.CheckConstraint(_TARGET, name="ck_release_change_target"),
        sa.CheckConstraint(_INTENT, name="ck_release_change_intent"),
    )
    op.create_table(
        "release_signing_decisions",
        sa.Column("decision_id", sa.LargeBinary(), nullable=False),
        sa.Column("bundle_sha256", sa.String(length=64), nullable=False),
        sa.Column("checksums_sha256", sa.String(length=64), nullable=False),
        sa.Column("signature_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_commit", sa.String(length=40), nullable=False),
        sa.Column("package_version", sa.String(length=64), nullable=False),
        sa.Column("signer_authority_id", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.LargeBinary(), nullable=False),
        sa.Column("key_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("registry_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("policy_revision_id", sa.LargeBinary(), nullable=False),
        sa.Column("signature_format", sa.String(length=32), nullable=False),
        sa.Column("namespace", sa.String(length=64), nullable=False),
        sa.Column("executor_identity", sa.LargeBinary(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signature", sa.LargeBinary(), nullable=False),
        sa.Column("evidence", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("decision_id", name="pk_release_signing_decisions"),
        sa.ForeignKeyConstraint(
            ["key_id", "signer_authority_id"],
            ["release_signing_keys.key_id", "release_signing_keys.signer_authority_id"],
            name="fk_release_decision_key_authority",
        ),
        sa.ForeignKeyConstraint(
            ["registry_revision_id"], ["release_registry_set_revisions.revision_id"],
            name="fk_release_decision_registry_revision",
        ),
        sa.CheckConstraint(
            "length(decision_id) > 0", name="ck_release_decision_present"
        ),
        sa.CheckConstraint(
            "length(executor_identity) > 0", name="ck_release_executor_present"
        ),
        sa.CheckConstraint(
            "length(signature) > 0", name="ck_release_signature_present"
        ),
        sa.CheckConstraint("length(evidence) > 0", name="ck_release_evidence_present"),
        sa.CheckConstraint(
            "signature_format = 'SSHSIG-Ed25519'",
            name="ck_release_decision_signature_format",
        ),
        sa.CheckConstraint(
            "namespace = 'liquent-operations-release-v1'",
            name="ck_release_decision_namespace",
        ),
    )


def downgrade() -> None:
    op.drop_table("release_signing_decisions")
    op.drop_table("release_registry_lifecycle_changes")
    op.drop_table("release_registry_current_set")
    op.drop_table("release_registry_revision_keys")
    op.drop_table("release_registry_revision_lifecycle_authorities")
    op.drop_table("release_registry_revision_signers")
    op.drop_table("release_registry_set_revisions")
    op.drop_table("release_signing_keys")
    op.drop_table("release_registry_lifecycle_authorities")
    op.drop_table("release_signer_authorities")
