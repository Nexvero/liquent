from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    IssuedBrowserSession,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.persistence.browser_sessions import DatabaseBrowserSessions
from liquent_platform.persistence.database import build_engine

pytestmark = pytest.mark.postgres_integration
NOW = datetime(2026, 8, 12, tzinfo=UTC)


def test_concurrent_rotation_has_at_most_one_replacement(
    postgres_engine: Engine, postgres_url: str
) -> None:
    current = SessionId("current-190")
    record = BrowserSessionRecord(
        ResolvedBrowserSession(SessionPrincipal(UserId("user-190")), "csrf"),
        NOW + timedelta(hours=1),
    )
    store = DatabaseBrowserSessions(postgres_engine, now=lambda: NOW)
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES (:user,'active')"
        ), {"user": b"user-190"})
    assert store.add_session(current, record) is True
    start = threading.Barrier(2)
    outcomes: list[bool] = []
    guard = threading.Lock()

    def rotate(name: str) -> None:
        engine = build_engine(postgres_url)
        try:
            participant = DatabaseBrowserSessions(engine, now=lambda: NOW)
            start.wait(timeout=15)
            result = participant.rotate_session(
                current,
                IssuedBrowserSession(
                    SessionId(f"replacement-{name}"),
                    f"csrf-{name}",
                    NOW + timedelta(hours=1),
                ),
            )
        finally:
            engine.dispose()
        with guard:
            outcomes.append(result)

    threads = [threading.Thread(target=rotate, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert sorted(outcomes) == [False, True]
