from __future__ import annotations

import threading

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.oidc_trust_bootstrap import (
    DatabaseInitialOidcTrustAuthorityBootstrap,
)

pytestmark = pytest.mark.postgres_integration


def test_concurrent_bootstrap_has_exactly_one_winner(
    postgres_engine: Engine, postgres_url: str
) -> None:
    users = (UserId("trust-bootstrap-a"), UserId("trust-bootstrap-b"))
    with postgres_engine.begin() as connection:
        for user in users:
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,'active')"),
                {"user": str(user).encode()},
            )
    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(user: UserId) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseInitialOidcTrustAuthorityBootstrap(engine)
            start.wait(timeout=15)
            outcome: object = store.bootstrap(user)
        except Exception as error:
            outcome = error
        finally:
            engine.dispose()
        with guard:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt, args=(user,)) for user in users]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert len(outcomes) == 2
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(outcome is not None for outcome in outcomes) == 1
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
