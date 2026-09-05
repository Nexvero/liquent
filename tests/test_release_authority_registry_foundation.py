from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.release_authority import (
    ReleaseAuthorityStatus,
    ReleaseActivationReviewerId,
    ReleaseEmergencyRevocationId,
    ReleasePolicyRevisionId,
    ReleasePolicyStatus,
    ReleasePromotionVerifierId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistryRecoveryId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningDecisionId,
    ReleaseSigningKeyId,
    ReleaseSigningKeyStatus,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


IDENTIFIER_TYPES = (
    ReleaseSignerAuthorityId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseSigningKeyId,
    ReleaseRegistrySetRevisionId,
    ReleasePolicyRevisionId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseSigningDecisionId,
    ReleaseRegistryRecoveryId,
    ReleaseEmergencyRevocationId,
    ReleaseRegistryBootstrapId,
    ReleaseActivationReviewerId,
    ReleasePromotionVerifierId,
)
TABLES = (
    "release_signer_authorities",
    "release_registry_lifecycle_authorities",
    "release_signing_keys",
    "release_registry_set_revisions",
    "release_registry_revision_signers",
    "release_registry_revision_lifecycle_authorities",
    "release_registry_revision_keys",
    "release_registry_current_set",
    "release_registry_lifecycle_changes",
    "release_signing_decisions",
)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'release-authority.db'}")

    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


@pytest.mark.parametrize("kind", IDENTIFIER_TYPES)
def test_release_identifiers_are_immutable_slotted_and_repr_free(kind: type) -> None:
    identifier = kind("opaque-lq240")

    assert [item.name for item in fields(kind)] == ["value"]
    assert "opaque-lq240" not in repr(identifier)
    assert not hasattr(identifier, "__dict__")
    with pytest.raises(FrozenInstanceError):
        identifier.value = "other"  # type: ignore[misc]


@pytest.mark.parametrize("kind", IDENTIFIER_TYPES)
@pytest.mark.parametrize("value", ["", None, 1, b"bytes", True])
def test_release_identifiers_reject_empty_or_non_string_values(
    kind: type, value: object,
) -> None:
    with pytest.raises(ValueError):
        kind(value)


def test_release_status_vocabularies_are_closed() -> None:
    assert {item.value for item in ReleaseAuthorityStatus} == {"active", "inactive"}
    assert {item.value for item in ReleaseSigningKeyStatus} == {
        "active", "inactive", "expired", "revoked"
    }
    assert {item.value for item in ReleasePolicyStatus} == {"active", "inactive"}


def test_secure_material_draws_twelve_independent_release_identifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(f"release-{index}" for index in range(12))
    monkeypatch.setattr("secrets.token_urlsafe", lambda _: next(values))
    material = SecureIdentityAuthorityMaterialGenerator()

    generated = (
        material.new_release_signer_authority_id(),
        material.new_release_registry_lifecycle_authority_id(),
        material.new_release_signing_key_id(),
        material.new_release_registry_set_revision_id(),
        material.new_release_policy_revision_id(),
        material.new_release_registry_lifecycle_change_id(),
        material.new_release_signing_decision_id(),
        material.new_release_registry_recovery_id(),
        material.new_release_emergency_revocation_id(),
        material.new_release_registry_bootstrap_id(),
        material.new_release_activation_reviewer_id(),
        material.new_release_promotion_verifier_id(),
    )
    assert tuple(item.value for item in generated) == tuple(
        f"release-{index}" for index in range(12)
    )


def test_migration_creates_only_empty_release_inventories(engine: Engine) -> None:
    existing = set(inspect(engine).get_table_names())
    assert set(TABLES) <= existing
    with engine.connect() as connection:
        assert all(
            connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0
            for table in TABLES
        )


def test_historical_revisions_remain_distinct_when_current_pointer_moves(
    engine: Engine,
) -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO release_signer_authorities VALUES (X'73')"
        ))
        connection.execute(text(
            "INSERT INTO release_registry_lifecycle_authorities VALUES (X'6c')"
        ))
        connection.execute(text(
            "INSERT INTO release_signing_keys VALUES "
            "(X'6b',X'73','ssh-ed25519','liquent-operations-release-v1',"
            "'SHA256:foundation','ssh-ed25519 PUBLIC')"
        ))
        for revision, signer_status, key_status in (
            ("72", "active", "active"),
            ("6e", "inactive", "revoked"),
        ):
            connection.execute(text(
                "INSERT INTO release_registry_set_revisions VALUES "
                f"(X'{revision}',X'70','active')"
            ))
            connection.execute(text(
                "INSERT INTO release_registry_revision_signers VALUES "
                f"(X'{revision}',X'73','{signer_status}')"
            ))
            connection.execute(text(
                "INSERT INTO release_registry_revision_lifecycle_authorities VALUES "
                f"(X'{revision}',X'6c','active')"
            ))
            connection.execute(text(
                "INSERT INTO release_registry_revision_keys VALUES "
                f"(X'{revision}',X'6b',X'73','{key_status}')"
            ))
        connection.execute(text(
            "INSERT INTO release_registry_current_set VALUES (1,X'6e')"
        ))

    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT status FROM release_registry_revision_signers "
            "WHERE revision_id=X'72'"
        )).scalar_one() == "active"
        assert connection.execute(text(
            "SELECT status FROM release_registry_revision_keys "
            "WHERE revision_id=X'6e'"
        )).scalar_one() == "revoked"
        assert connection.scalar(text(
            "SELECT revision_id FROM release_registry_current_set"
        )) == b"n"


def test_key_material_is_immutable_and_registry_wide_unique(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO release_signer_authorities VALUES (X'61'),(X'62')"
        ))
        connection.execute(text(
            "INSERT INTO release_signing_keys VALUES "
            "(X'31',X'61','ssh-ed25519','liquent-operations-release-v1',"
            "'SHA256:one','ssh-ed25519 ONE')"
        ))
        connection.execute(text(
            "INSERT INTO release_registry_set_revisions VALUES "
            "(X'72',X'70','active')"
        ))
        connection.execute(text(
            "INSERT INTO release_registry_revision_keys VALUES "
            "(X'72',X'31',X'61','inactive')"
        ))

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_signing_keys VALUES "
                "(X'32',X'62','ssh-ed25519','liquent-operations-release-v1',"
                "'SHA256:one','ssh-ed25519 TWO')"
            ))
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "UPDATE release_signing_keys SET signer_authority_id=X'62' "
                "WHERE key_id=X'31'"
            ))


def test_lifecycle_change_requires_exactly_one_typed_target(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO release_signer_authorities VALUES (X'73')"
        ))
        connection.execute(text(
            "INSERT INTO release_registry_lifecycle_authorities VALUES (X'6c')"
        ))
        connection.execute(text(
            "INSERT INTO release_registry_set_revisions VALUES "
            "(X'72',X'70','active'),(X'6e',X'70','active')"
        ))

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_registry_lifecycle_changes VALUES "
                "(X'63',X'6c','signer',X'73',X'6c',NULL,'grant',X'72',X'6e')"
            ))


def test_current_pointer_and_signing_decision_cannot_reference_unknown_facts(
    engine: Engine,
) -> None:
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_registry_current_set VALUES (1,X'6d')"
            ))
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_signing_decisions VALUES ("
                "X'64','a','b','c','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',"
                "'1.0.0',X'73',X'6b','SHA256:key',X'72',X'70',"
                "'SSHSIG-Ed25519','liquent-operations-release-v1',X'65',"
                "CURRENT_TIMESTAMP,X'73',X'65')"
            ))
