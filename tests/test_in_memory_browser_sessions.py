from datetime import UTC, datetime, timedelta

from liquent_platform.identity.access import UserId
from liquent_platform.identity.in_memory import InMemoryBrowserSessions
from liquent_platform.identity.ports import BrowserSessionLookup
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)


NOW = datetime(2026, 7, 27, 12, tzinfo=UTC)
SESSION_ID = SessionId("opaque-session")


def _session() -> ResolvedBrowserSession:
    return ResolvedBrowserSession(
        SessionPrincipal(UserId("user-1")),
        "private-csrf-proof",
    )


def _lookup(
    port: BrowserSessionLookup,
    session_id: SessionId,
) -> ResolvedBrowserSession | None:
    return port.get_session(session_id)


def test_active_record_resolves_through_lookup_port() -> None:
    session = _session()
    sessions = InMemoryBrowserSessions(
        {SESSION_ID: BrowserSessionRecord(session, NOW + timedelta(minutes=1))},
        now=lambda: NOW,
    )

    assert _lookup(sessions, SESSION_ID) is session


def test_unknown_session_is_neutral_without_reading_clock() -> None:
    clock_reads = 0

    def now() -> datetime:
        nonlocal clock_reads
        clock_reads += 1
        return NOW

    sessions = InMemoryBrowserSessions({}, now=now)

    assert sessions.get_session(SessionId("unknown-session")) is None
    assert clock_reads == 0


def test_expired_record_is_neutral_none() -> None:
    sessions = InMemoryBrowserSessions(
        {SESSION_ID: BrowserSessionRecord(_session(), NOW)},
        now=lambda: NOW,
    )

    assert sessions.get_session(SESSION_ID) is None


def test_revoked_record_is_neutral_none() -> None:
    sessions = InMemoryBrowserSessions(
        {
            SESSION_ID: BrowserSessionRecord(
                _session(),
                NOW + timedelta(minutes=1),
                revoked_at=NOW,
            )
        },
        now=lambda: NOW,
    )

    assert sessions.get_session(SESSION_ID) is None


def test_constructor_copies_supplied_records() -> None:
    session = _session()
    records = {
        SESSION_ID: BrowserSessionRecord(session, NOW + timedelta(minutes=1))
    }
    sessions = InMemoryBrowserSessions(records, now=lambda: NOW)
    records.clear()

    assert sessions.get_session(SESSION_ID) is session
