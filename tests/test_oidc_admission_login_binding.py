from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_admission_login_binding import (
    DatabaseOidcPendingLoginAdmissionBinding,
)

NOW = datetime(2026, 9, 8, 17, tzinfo=UTC)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'binding.db'}")
    upgrade_to_head(str(database.url))
    with database.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users (user_id,status) VALUES (x'75','active')"
        ))
        connection.execute(text(
            "INSERT INTO identity_workspaces (workspace_id,status)"
            " VALUES (x'77','active')"
        ))
        connection.execute(text(
            "INSERT INTO identity_admissions"
            " (admission_id,provisioning_request,target_user_id,"
            " target_workspace_id,lifetime_microseconds,expires_at,consumed_at,"
            " bound_issuer,bound_subject) VALUES"
            " (x'61',x'72',x'75',x'77',600000000,:expires,NULL,NULL,NULL)"
        ), {"expires": NOW + timedelta(minutes=10)})
    try:
        yield database
    finally:
        database.dispose()


def _pending() -> PendingOidcLoginTransaction:
    return PendingOidcLoginTransaction(
        expected_issuer="https://issuer.example",
        expected_nonce="nonce",
        code_verifier="verifier",
        redirect_uri="https://app.example/callback",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )


def _add(engine: Engine, state: str) -> None:
    from liquent_platform.persistence.oidc_login_transactions import (
        DatabaseOidcLoginTransactions,
    )

    assert DatabaseOidcLoginTransactions(engine, now=lambda: NOW).add_transaction(
        OidcLoginState(state), _pending()
    )


def test_binds_without_caller_selected_state_and_exact_retry(engine: Engine) -> None:
    _add(engine, "only-state")
    store = DatabaseOidcPendingLoginAdmissionBinding(engine, now=lambda: NOW)

    assert store.bind_admission(IdentityAdmissionId("a")) is True
    assert store.bind_admission(IdentityAdmissionId("a")) is True

    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT state,admission_id FROM oidc_login_transactions"
        )).one()
    assert bytes(row.state) == b"only-state"
    assert bytes(row.admission_id) == b"a"
    assert repr(store) == "DatabaseOidcPendingLoginAdmissionBinding()"


def test_zero_or_ambiguous_pending_logins_are_neutral(engine: Engine) -> None:
    store = DatabaseOidcPendingLoginAdmissionBinding(engine, now=lambda: NOW)
    assert store.bind_admission(IdentityAdmissionId("a")) is False

    _add(engine, "state-one")
    _add(engine, "state-two")
    assert store.bind_admission(IdentityAdmissionId("a")) is False
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM oidc_login_transactions"
            " WHERE admission_id IS NOT NULL"
        )) == 0


def test_unknown_or_expired_admission_is_neutral(engine: Engine) -> None:
    _add(engine, "only-state")
    store = DatabaseOidcPendingLoginAdmissionBinding(engine, now=lambda: NOW)
    assert store.bind_admission(IdentityAdmissionId("unknown")) is False
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE identity_admissions SET expires_at=:expired"
        ), {"expired": NOW})
    assert store.bind_admission(IdentityAdmissionId("a")) is False
