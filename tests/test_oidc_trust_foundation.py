from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustChangeId,
    OidcTrustRevisionId,
)
from liquent_platform.identity.ports import OidcTrustManagementAuthorityLookup
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityStoreUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_trust_authority import (
    DatabaseOidcTrustManagementAuthority,
)

ACTOR = UserId("actor-199")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'trust.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _facts(engine: Engine, *, actor: str = "active", authority: str | None = "active") -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:actor,:status)"),
            {"actor": str(ACTOR).encode(), "status": actor},
        )
        if authority is not None:
            connection.execute(
                text(
                    "INSERT INTO oidc_trust_management_authorities"
                    " VALUES (:actor,:status)"
                ),
                {"actor": str(ACTOR).encode(), "status": authority},
            )


def test_revision_and_change_ids_are_stable_repr_free_values() -> None:
    revision = OidcTrustRevisionId("revision-199")
    change = OidcTrustChangeId("change-199")
    assert revision.value == "revision-199"
    assert change.value == "change-199"
    assert "revision-199" not in repr(revision)
    assert "change-199" not in repr(change)
    with pytest.raises(FrozenInstanceError):
        revision.value = "other"  # type: ignore[misc]


@pytest.mark.parametrize("kind", [OidcTrustRevisionId, OidcTrustChangeId])
@pytest.mark.parametrize("value", ["", None, 1, True])
def test_trust_identifiers_reject_invalid_values(kind, value) -> None:
    with pytest.raises(ValueError):
        kind(value)


def test_secure_material_generates_independent_trust_ids(monkeypatch) -> None:
    draws = iter(["revision", "change"])
    monkeypatch.setattr(
        "liquent_platform.identity.authority_material.secrets.token_urlsafe",
        lambda _: next(draws),
    )
    material = SecureIdentityAuthorityMaterialGenerator()
    assert material.new_oidc_trust_revision_id() == OidcTrustRevisionId("revision")
    assert material.new_oidc_trust_change_id() == OidcTrustChangeId("change")


def test_current_active_actor_and_authority_permit(engine: Engine) -> None:
    _facts(engine)
    lookup: OidcTrustManagementAuthorityLookup = (
        DatabaseOidcTrustManagementAuthority(engine)
    )
    assert lookup.permits_oidc_trust_management(SessionPrincipal(ACTOR)) is True


@pytest.mark.parametrize(
    ("actor", "authority"),
    [("inactive", "active"), ("active", "inactive"), ("active", None)],
)
def test_absence_or_inactivity_fails_closed(
    engine: Engine, actor: str, authority: str | None
) -> None:
    _facts(engine, actor=actor, authority=authority)
    lookup = DatabaseOidcTrustManagementAuthority(engine)
    assert lookup.permits_oidc_trust_management(SessionPrincipal(ACTOR)) is False


def test_committed_revocation_affects_later_lookup(engine: Engine) -> None:
    _facts(engine)
    lookup = DatabaseOidcTrustManagementAuthority(engine)
    principal = SessionPrincipal(ACTOR)
    assert lookup.permits_oidc_trust_management(principal) is True
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE oidc_trust_management_authorities SET status='inactive'")
        )
    assert lookup.permits_oidc_trust_management(principal) is False


def test_unmigrated_store_is_detail_free_technical_unavailability(
    tmp_path: Path,
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    lookup = DatabaseOidcTrustManagementAuthority(engine)
    try:
        with pytest.raises(OidcTrustAuthorityStoreUnavailable) as raised:
            lookup.permits_oidc_trust_management(SessionPrincipal(ACTOR))
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(lookup) == "DatabaseOidcTrustManagementAuthority()"
    finally:
        engine.dispose()


def test_migration_creates_empty_authority_and_revision_foundation(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT count(*) FROM oidc_trust_management_authorities")
        ) == 0
        assert connection.scalar(text("SELECT count(*) FROM oidc_trust_revisions")) == 0
