from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityRecoveryId,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityRecoveryId,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


IDENTIFIER_TYPES = (
    OidcTrustAuthoritySetRevisionId,
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityRecoveryId,
    WorkspaceMembershipAuthoritySetRevisionId,
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityRecoveryId,
)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'authority-lifecycle.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


@pytest.mark.parametrize("kind", IDENTIFIER_TYPES)
def test_lifecycle_identifiers_are_immutable_slotted_and_repr_free(kind) -> None:
    identifier = kind("opaque-212")

    assert [item.name for item in fields(kind)] == ["value"]
    assert "opaque-212" not in repr(identifier)
    assert not hasattr(identifier, "__dict__")
    with pytest.raises(FrozenInstanceError):
        identifier.value = "other"  # type: ignore[misc]


@pytest.mark.parametrize("kind", IDENTIFIER_TYPES)
@pytest.mark.parametrize("value", ["", None, 1, b"bytes"])
def test_lifecycle_identifiers_reject_invalid_values(kind, value) -> None:
    with pytest.raises(ValueError):
        kind(value)


def test_secure_material_draws_six_independent_lifecycle_identifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(f"lifecycle-{index}" for index in range(6))
    monkeypatch.setattr("secrets.token_urlsafe", lambda _: next(values))
    material = SecureIdentityAuthorityMaterialGenerator()

    generated = (
        material.new_oidc_trust_authority_set_revision_id(),
        material.new_oidc_trust_authority_lifecycle_change_id(),
        material.new_oidc_trust_authority_recovery_id(),
        material.new_workspace_membership_authority_set_revision_id(),
        material.new_workspace_membership_authority_lifecycle_change_id(),
        material.new_workspace_membership_authority_recovery_id(),
    )
    assert tuple(identifier.value for identifier in generated) == tuple(
        f"lifecycle-{index}" for index in range(6)
    )


def test_all_lifecycle_foundations_start_empty(engine: Engine) -> None:
    tables = (
        "oidc_trust_authority_set_revisions",
        "oidc_trust_authority_set_members",
        "oidc_trust_authority_current_set",
        "oidc_trust_authority_lifecycle_changes",
        "oidc_trust_authority_recoveries",
        "workspace_membership_authority_set_revisions",
        "workspace_membership_authority_set_members",
        "workspace_membership_authority_current_sets",
        "workspace_membership_authority_lifecycle_changes",
        "workspace_membership_authority_recoveries",
    )
    with engine.connect() as connection:
        assert all(
            connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0
            for table in tables
        )


def test_existing_bootstrap_authorities_are_not_silently_anchored(
    engine: Engine,
) -> None:
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO identity_users VALUES (X'75','active')"))
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (X'77','active')")
        )
        connection.execute(
            text("INSERT INTO oidc_trust_management_authorities VALUES (X'75','active')")
        )
        connection.execute(text(
            "INSERT INTO workspace_membership_management_authorities VALUES "
            "(X'75',X'77','active')"
        ))

    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM oidc_trust_authority_current_set"
        )) == 0
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_authority_current_sets"
        )) == 0
        assert connection.scalar(text(
            "SELECT count(*) FROM oidc_trust_authority_set_revisions"
        )) == 0
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_authority_set_revisions"
        )) == 0


def test_non_anchor_change_requires_an_expected_revision(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO identity_users VALUES (X'75','active')"))
        connection.execute(text(
            "INSERT INTO oidc_trust_authority_set_revisions VALUES (X'72')"
        ))
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO oidc_trust_authority_lifecycle_changes VALUES "
                "(X'63',X'75',X'75','grant',NULL,X'72')"
            ))


def test_membership_current_revision_cannot_cross_workspace_scope(
    engine: Engine,
) -> None:
    foreign_keys = inspect(engine).get_foreign_keys(
        "workspace_membership_authority_current_sets"
    )

    assert any(
        key["constrained_columns"] == ["revision_id", "workspace_id"]
        and key["referred_columns"] == ["revision_id", "workspace_id"]
        for key in foreign_keys
    )
