from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine

from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.oidc_login_transactions import (
    DatabaseOidcLoginTransactions,
)

pytestmark = pytest.mark.postgres_integration
NOW = datetime(2026, 8, 12, tzinfo=UTC)
STATE = OidcLoginState("state-189")


def _pending() -> PendingOidcLoginTransaction:
    return PendingOidcLoginTransaction(
        expected_issuer="https://idp.example",
        expected_nonce="nonce",
        code_verifier="verifier",
        redirect_uri="https://app.example/callback",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )


def test_concurrent_claim_returns_pending_exactly_once(
    postgres_engine: Engine, postgres_url: str
) -> None:
    store = DatabaseOidcLoginTransactions(postgres_engine, now=lambda: NOW)
    pending = _pending()
    assert store.add_transaction(STATE, pending) is True
    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def claim() -> None:
        engine = build_engine(postgres_url)
        try:
            participant = DatabaseOidcLoginTransactions(engine, now=lambda: NOW)
            start.wait(timeout=15)
            result: object = participant.claim_transaction(STATE)
        except Exception as error:
            result = error
        finally:
            engine.dispose()
        with guard:
            outcomes.append(result)

    threads = [threading.Thread(target=claim) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert outcomes.count(pending) == 1
    assert outcomes.count(None) == 1
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
