from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.oidc_trust import BootstrappedOidcTrustAuthority
from liquent_platform.identity.ports import InitialOidcTrustAuthorityBootstrap
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityBootstrapUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_trust_bootstrap import (
    DatabaseInitialOidcTrustAuthorityBootstrap,
)

USER = UserId("trust-bootstrap-user")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'trust-bootstrap.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _user(engine: Engine, user: UserId = USER, status: str = "active") -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:user,:status)"),
            {"user": str(user).encode(), "status": status},
        )


def test_port_grants_existing_active_user_once(engine: Engine) -> None:
    _user(engine)
    port: InitialOidcTrustAuthorityBootstrap = (
        DatabaseInitialOidcTrustAuthorityBootstrap(engine)
    )
    assert port.bootstrap(USER) == BootstrappedOidcTrustAuthority(USER)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT user_id,status FROM oidc_trust_management_authorities")
        ).one() == (str(USER).encode(), "active")


@pytest.mark.parametrize("known", [False, True])
def test_unknown_or_inactive_target_is_neutral_and_writes_nothing(
    engine: Engine, known: bool
) -> None:
    if known:
        _user(engine, status="inactive")
    store = DatabaseInitialOidcTrustAuthorityBootstrap(engine)
    assert store.bootstrap(USER) is None
    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT count(*) FROM oidc_trust_management_authorities")
        ) == 0


def test_any_existing_authority_permanently_closes_bootstrap(engine: Engine) -> None:
    _user(engine)
    store = DatabaseInitialOidcTrustAuthorityBootstrap(engine)
    assert store.bootstrap(USER) is not None
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE oidc_trust_management_authorities SET status='inactive'")
        )
    other = UserId("other-user")
    _user(engine, other)
    assert store.bootstrap(other) is None
    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT count(*) FROM oidc_trust_management_authorities")
        ) == 1


def test_bootstrap_creates_no_revision_or_active_configuration(engine: Engine) -> None:
    _user(engine)
    assert DatabaseInitialOidcTrustAuthorityBootstrap(engine).bootstrap(USER)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM oidc_trust_revisions")) == 0
        assert connection.scalar(
            text("SELECT count(*) FROM oidc_client_configuration")
        ) == 0


def test_invalid_target_is_detail_free_technical_unavailability(engine: Engine) -> None:
    store = DatabaseInitialOidcTrustAuthorityBootstrap(engine)
    with pytest.raises(OidcTrustAuthorityBootstrapUnavailable) as raised:
        store.bootstrap(UserId(""))
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_unmigrated_store_is_detail_free_technical_unavailability(
    tmp_path: Path,
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = DatabaseInitialOidcTrustAuthorityBootstrap(engine)
    try:
        with pytest.raises(OidcTrustAuthorityBootstrapUnavailable) as raised:
            store.bootstrap(USER)
        assert raised.value.args == ("oidc_trust_authority_bootstrap_unavailable",)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseInitialOidcTrustAuthorityBootstrap()"
    finally:
        engine.dispose()
