from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.oidc_trust import OidcTrustRevisionId
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcLoginTransactionStoreUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_login_transactions import (
    DatabaseOidcLoginTransactions,
)

NOW = datetime(2026, 8, 12, tzinfo=UTC)
STATE = OidcLoginState("state-1")


def _pending(expires: datetime | None = None) -> PendingOidcLoginTransaction:
    return PendingOidcLoginTransaction(
        expected_issuer="https://idp.example",
        expected_nonce="nonce-1",
        code_verifier="verifier-1",
        redirect_uri="https://app.example/callback",
        created_at=NOW - timedelta(minutes=1),
        expires_at=expires or NOW + timedelta(minutes=1),
        expected_trust_revision=OidcTrustRevisionId("trust-revision-201"),
        admission_id=IdentityAdmissionId("admission-1"),
        return_path="/research",
    )


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'login.db'}")
    upgrade_to_head(str(database.url))
    with database.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO oidc_trust_revisions"
                " (revision_id,issuer,authorization_endpoint,client_id,"
                " redirect_uri,scopes,token_endpoint,jwks_uri,"
                " allowed_signing_algorithms,clock_skew_microseconds) VALUES"
                " (:revision,:issuer,:authorization,:client,:redirect,:scopes,"
                " :token,:jwks,:algorithms,:skew)"
            ),
            {
                "revision": b"trust-revision-201",
                "issuer": b"https://idp.example",
                "authorization": b"https://idp.example/authorize",
                "client": b"client",
                "redirect": b"https://app.example/callback",
                "scopes": b'["openid"]',
                "token": b"https://idp.example/token",
                "jwks": b"https://idp.example/jwks",
                "algorithms": b'["RS256"]',
                "skew": 0,
            },
        )
    try:
        yield database
    finally:
        database.dispose()


def test_add_claim_and_permanent_non_reuse(engine: Engine) -> None:
    store = DatabaseOidcLoginTransactions(engine, now=lambda: NOW)
    pending = _pending()

    assert store.add_transaction(STATE, pending) is True
    assert store.claim_transaction(STATE) == pending
    assert store.claim_transaction(STATE) is None
    assert store.add_transaction(STATE, _pending()) is False

    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT * FROM oidc_login_transactions WHERE state=:state"),
            {"state": STATE.value.encode()},
        ).mappings().one()
    assert row["status"] == "used"
    assert all(
        row[name] is None
        for name in (
            "expected_issuer",
            "expected_nonce",
            "code_verifier",
            "redirect_uri",
            "expected_trust_revision",
            "created_at",
            "expires_at",
            "admission_id",
            "return_path",
        )
    )


def test_expired_claim_scrubs_secrets_and_returns_neutral_none(engine: Engine) -> None:
    store = DatabaseOidcLoginTransactions(engine, now=lambda: NOW)
    assert store.add_transaction(STATE, _pending(expires=NOW)) is True

    assert store.claim_transaction(STATE) is None
    assert store.add_transaction(STATE, _pending()) is False


def test_unknown_claim_does_not_reserve_state(engine: Engine) -> None:
    store = DatabaseOidcLoginTransactions(engine, now=lambda: NOW)

    assert store.claim_transaction(STATE) is None
    assert store.add_transaction(STATE, _pending()) is True


def test_collision_keeps_original_pending_record(engine: Engine) -> None:
    store = DatabaseOidcLoginTransactions(engine, now=lambda: NOW)
    original = _pending()
    changed = replace(original, expected_nonce="other")
    assert store.add_transaction(STATE, original) is True
    assert store.add_transaction(STATE, changed) is False
    assert store.claim_transaction(STATE) == original


def test_technical_failure_is_detail_free(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = DatabaseOidcLoginTransactions(engine, now=lambda: NOW)
    try:
        with pytest.raises(OidcLoginTransactionStoreUnavailable) as raised:
            store.add_transaction(STATE, _pending())
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseOidcLoginTransactions()"
    finally:
        engine.dispose()
