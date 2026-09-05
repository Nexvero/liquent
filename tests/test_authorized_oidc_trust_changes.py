from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustChangeId,
    OidcTrustChangeKind,
    OidcTrustRevisionId,
)
from liquent_platform.identity.ports import AuthorizedOidcTrustChangeStore
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcTrustChangeConflict,
    OidcTrustChangeStoreUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_client_configuration import (
    DatabaseActiveOidcClientConfiguration,
)
from liquent_platform.persistence.oidc_trust_changes import (
    DatabaseAuthorizedOidcTrustChanges,
)

ACTOR = UserId("actor-202")
PRINCIPAL = SessionPrincipal(ACTOR)
CHANGE = OidcTrustChangeId("change-202")
REVISION_1 = OidcTrustRevisionId("revision-202-1")
REVISION_2 = OidcTrustRevisionId("revision-202-2")


def _configuration(client: str = "client-1") -> TrustedOidcClientConfiguration:
    return TrustedOidcClientConfiguration(
        issuer="https://idp.example",
        authorization_endpoint="https://idp.example/authorize",
        client_id=client,
        redirect_uri="https://app.example/callback",
        scopes=("openid", "profile"),
        token_endpoint="https://idp.example/token",
        jwks_uri="https://idp.example/jwks",
        allowed_signing_algorithms=("RS256",),
        clock_skew=timedelta(seconds=30),
    )


class Source:
    def __init__(self, *values: Any) -> None:
        self.values = list(values)
        self.calls = 0

    def __call__(self) -> Any:
        value = self.values[self.calls]
        self.calls += 1
        if isinstance(value, BaseException):
            raise value
        return value


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'trust-change.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _authority(engine: Engine, *, active: bool = True) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users (user_id,status) VALUES (:user,'active')"),
            {"user": ACTOR.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO oidc_trust_management_authorities (user_id,status)"
                " VALUES (:user,:status)"
            ),
            {"user": ACTOR.encode(), "status": "active" if active else "inactive"},
        )


def _store(engine: Engine, source: Source) -> DatabaseAuthorizedOidcTrustChanges:
    store: AuthorizedOidcTrustChangeStore = DatabaseAuthorizedOidcTrustChanges(
        engine, generate_revision_id=source
    )
    return store  # type: ignore[return-value]


def test_authorized_initial_activation_creates_revision_and_active_snapshot(
    engine: Engine,
) -> None:
    _authority(engine)
    source = Source(REVISION_1)

    result = _store(engine, source).change_trust(
        CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
    )

    assert result is not None and result.revision_id == REVISION_1
    assert source.calls == 1
    trust = DatabaseActiveOidcClientConfiguration(engine).get_active_trust()
    assert trust is not None
    assert trust.revision_id == REVISION_1
    assert trust.configuration == _configuration()


def test_exact_retry_survives_authority_revocation_without_second_revision(
    engine: Engine,
) -> None:
    _authority(engine)
    first_source = Source(REVISION_1)
    store = _store(engine, first_source)
    first = store.change_trust(
        CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
    )
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE oidc_trust_management_authorities SET status='inactive'"
        ))
    retry_source = Source(REVISION_2)

    repeated = _store(engine, retry_source).change_trust(
        CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
    )

    assert repeated == first
    assert retry_source.calls == 0


def test_same_change_with_different_configuration_is_conflict(engine: Engine) -> None:
    _authority(engine)
    store = _store(engine, Source(REVISION_1))
    assert store.change_trust(
        CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
    ) is not None

    with pytest.raises(OidcTrustChangeConflict):
        store.change_trust(
            CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None,
            _configuration("different-client"),
        )


def test_reusing_change_with_different_actor_or_intent_is_conflict(
    engine: Engine,
) -> None:
    _authority(engine)
    store = _store(engine, Source(REVISION_1))
    assert store.change_trust(
        CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
    ) is not None

    with pytest.raises(OidcTrustChangeConflict):
        store.change_trust(
            CHANGE, SessionPrincipal(UserId("other-actor")),
            OidcTrustChangeKind.ACTIVATE, None, _configuration(),
        )
    with pytest.raises(OidcTrustChangeConflict):
        store.change_trust(
            CHANGE, PRINCIPAL, OidcTrustChangeKind.DEACTIVATE, REVISION_1, None,
        )


def test_rotation_requires_exact_current_revision_and_creates_a_new_one(
    engine: Engine,
) -> None:
    _authority(engine)
    source = Source(REVISION_1, REVISION_2)
    store = _store(engine, source)
    assert store.change_trust(
        CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
    ) is not None

    rejected = store.change_trust(
        OidcTrustChangeId("wrong-precondition"), PRINCIPAL,
        OidcTrustChangeKind.ROTATE, OidcTrustRevisionId("other"),
        _configuration("client-2"),
    )
    rotated = store.change_trust(
        OidcTrustChangeId("rotation"), PRINCIPAL, OidcTrustChangeKind.ROTATE,
        REVISION_1, _configuration("client-2"),
    )

    assert rejected is None
    assert rotated is not None and rotated.revision_id == REVISION_2
    assert source.calls == 2
    trust = DatabaseActiveOidcClientConfiguration(engine).get_active_trust()
    assert trust is not None and trust.revision_id == REVISION_2


def test_deactivation_is_revision_bound_and_stops_later_lookup(engine: Engine) -> None:
    _authority(engine)
    store = _store(engine, Source(REVISION_1))
    assert store.change_trust(
        CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
    ) is not None

    result = store.change_trust(
        OidcTrustChangeId("deactivate"), PRINCIPAL,
        OidcTrustChangeKind.DEACTIVATE, REVISION_1, None,
    )

    assert result is not None and result.revision_id is None
    assert DatabaseActiveOidcClientConfiguration(engine).get_active_trust() is None
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM oidc_trust_revisions")) == 1


def test_rotation_can_reactivate_only_from_the_retained_exact_revision(
    engine: Engine,
) -> None:
    _authority(engine)
    store = _store(engine, Source(REVISION_1, REVISION_2))
    assert store.change_trust(
        CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
    ) is not None
    assert store.change_trust(
        OidcTrustChangeId("off"), PRINCIPAL, OidcTrustChangeKind.DEACTIVATE,
        REVISION_1, None,
    ) is not None

    assert store.change_trust(
        OidcTrustChangeId("wrong-reactivation"), PRINCIPAL,
        OidcTrustChangeKind.ROTATE, OidcTrustRevisionId("wrong"),
        _configuration("client-2"),
    ) is None
    result = store.change_trust(
        OidcTrustChangeId("reactivation"), PRINCIPAL,
        OidcTrustChangeKind.ROTATE, REVISION_1, _configuration("client-2"),
    )
    assert result is not None and result.revision_id == REVISION_2


@pytest.mark.parametrize("authority", [False, None])
def test_missing_or_revoked_authority_is_neutral_without_generation(
    engine: Engine, authority: bool | None
) -> None:
    if authority is not None:
        _authority(engine, active=authority)
    source = Source(REVISION_1)

    assert _store(engine, source).change_trust(
        CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
    ) is None
    assert source.calls == 0


def test_generator_failure_rolls_back_everything(engine: Engine) -> None:
    _authority(engine)
    with pytest.raises(OidcTrustChangeStoreUnavailable):
        _store(engine, Source(RuntimeError("secret detail"))).change_trust(
            CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None, _configuration()
        )
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM oidc_trust_revisions")) == 0
        assert connection.scalar(text("SELECT count(*) FROM authorized_oidc_trust_changes")) == 0


@pytest.mark.parametrize(
    ("kind", "expected", "configuration"),
    [
        (OidcTrustChangeKind.ACTIVATE, REVISION_1, _configuration()),
        (OidcTrustChangeKind.ROTATE, None, _configuration()),
        (OidcTrustChangeKind.DEACTIVATE, REVISION_1, _configuration()),
    ],
)
def test_invalid_transition_shape_is_detail_free_technical_unavailability(
    engine: Engine,
    kind: OidcTrustChangeKind,
    expected: OidcTrustRevisionId | None,
    configuration: TrustedOidcClientConfiguration | None,
) -> None:
    with pytest.raises(OidcTrustChangeStoreUnavailable):
        _store(engine, Source(REVISION_1)).change_trust(
            CHANGE, PRINCIPAL, kind, expected, configuration
        )


def test_technical_failure_is_detail_free(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = _store(engine, Source(REVISION_1))
    try:
        with pytest.raises(OidcTrustChangeStoreUnavailable) as raised:
            store.change_trust(
                CHANGE, PRINCIPAL, OidcTrustChangeKind.ACTIVATE, None,
                _configuration(),
            )
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseAuthorizedOidcTrustChanges()"
    finally:
        engine.dispose()
