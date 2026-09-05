from datetime import UTC, datetime, timedelta
from pathlib import Path

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
from liquent_platform.persistence.identity_errors import BrowserSessionStoreUnavailable
from liquent_platform.persistence.migrate import upgrade_to_head

NOW = datetime(2026, 8, 12, tzinfo=UTC)
SESSION = SessionId("session-1")
PRINCIPAL = SessionPrincipal(UserId("user-1"))
RESOLVED = ResolvedBrowserSession(PRINCIPAL, "csrf-1")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'sessions.db'}")
    upgrade_to_head(str(database.url))
    with database.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES (:user,'active')"
        ), {"user": str(PRINCIPAL.user_id).encode()})
    try:
        yield database
    finally:
        database.dispose()


def _record(expires: datetime | None = None) -> BrowserSessionRecord:
    return BrowserSessionRecord(RESOLVED, expires or NOW + timedelta(hours=1))


def test_add_lookup_and_collision_non_reuse(engine: Engine) -> None:
    store = DatabaseBrowserSessions(engine, now=lambda: NOW)

    assert store.add_session(SESSION, _record()) is True
    assert store.get_session(SESSION) == RESOLVED
    assert store.add_session(SESSION, _record()) is False


def test_expired_and_revoked_lookup_fail_closed(engine: Engine) -> None:
    store = DatabaseBrowserSessions(engine, now=lambda: NOW)
    expired = SessionId("expired")
    revoked = SessionId("revoked")
    assert store.add_session(expired, _record(NOW)) is True
    assert store.add_session(revoked, _record()) is True
    store.revoke_session(revoked)

    assert store.get_session(expired) is None
    assert store.get_session(revoked) is None


def test_inactive_user_cannot_create_or_resolve_session(engine: Engine) -> None:
    store = DatabaseBrowserSessions(engine, now=lambda: NOW)
    assert store.add_session(SESSION, _record()) is True
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE identity_users SET status='inactive'"
        ))
    assert store.get_session(SESSION) is None
    assert store.add_session(SessionId("new"), _record()) is False


def test_rotation_reuses_principal_and_revokes_source_atomically(
    engine: Engine,
) -> None:
    store = DatabaseBrowserSessions(engine, now=lambda: NOW)
    assert store.add_session(SESSION, _record()) is True
    replacement = IssuedBrowserSession(
        SessionId("session-2"), "csrf-2", NOW + timedelta(hours=2)
    )

    assert store.rotate_session(SESSION, replacement) is True
    assert store.get_session(SESSION) is None
    assert store.get_session(replacement.session_id) == ResolvedBrowserSession(
        PRINCIPAL, "csrf-2"
    )


def test_rotation_collision_leaves_source_active(engine: Engine) -> None:
    store = DatabaseBrowserSessions(engine, now=lambda: NOW)
    assert store.add_session(SESSION, _record()) is True
    collision = IssuedBrowserSession(
        SessionId("collision"), "csrf-2", NOW + timedelta(hours=1)
    )
    assert store.add_session(collision.session_id, _record()) is True

    assert store.rotate_session(SESSION, collision) is False
    assert store.get_session(SESSION) == RESOLVED


def test_revocation_is_idempotent_and_retains_non_reusable_row(engine: Engine) -> None:
    store = DatabaseBrowserSessions(engine, now=lambda: NOW)
    assert store.add_session(SESSION, _record()) is True

    store.revoke_session(SESSION)
    store.revoke_session(SESSION)
    store.revoke_session(SessionId("unknown"))

    assert store.add_session(SESSION, _record()) is False
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM browser_sessions")) == 1


def test_technical_failure_is_detail_free(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = DatabaseBrowserSessions(engine, now=lambda: NOW)
    try:
        with pytest.raises(BrowserSessionStoreUnavailable) as raised:
            store.get_session(SESSION)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseBrowserSessions()"
    finally:
        engine.dispose()
