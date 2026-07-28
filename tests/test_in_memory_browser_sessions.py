from datetime import UTC, datetime, timedelta

from liquent_platform.identity.access import UserId
from liquent_platform.identity.in_memory import InMemoryBrowserSessions
from liquent_platform.identity.ports import (
    BrowserSessionCreationStore,
    BrowserSessionLookup,
    BrowserSessionRotationStore,
)
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    IssuedBrowserSession,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)


NOW = datetime(2026, 7, 27, 12, tzinfo=UTC)
SESSION_ID = SessionId("opaque-session")
REPLACEMENT_ID = SessionId("replacement-session")
REPLACEMENT_CSRF = "replacement-csrf-proof"


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


def _add(
    port: BrowserSessionCreationStore,
    session_id: SessionId,
    record: BrowserSessionRecord,
) -> bool:
    return port.add_session(session_id, record)


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


def test_add_session_is_available_through_creation_store_port() -> None:
    session = _session()
    record = BrowserSessionRecord(session, NOW + timedelta(minutes=1))
    sessions = InMemoryBrowserSessions({}, now=lambda: NOW)

    assert _add(sessions, SESSION_ID, record) is True
    assert _lookup(sessions, SESSION_ID) is session


def test_add_session_does_not_replace_existing_identifier() -> None:
    original = _session()
    replacement = ResolvedBrowserSession(
        SessionPrincipal(UserId("user-2")),
        "replacement-proof",
    )
    sessions = InMemoryBrowserSessions(
        {
            SESSION_ID: BrowserSessionRecord(
                original,
                NOW + timedelta(minutes=1),
            )
        },
        now=lambda: NOW,
    )

    assert (
        sessions.add_session(
            SESSION_ID,
            BrowserSessionRecord(replacement, NOW + timedelta(minutes=2)),
        )
        is False
    )
    assert sessions.get_session(SESSION_ID) is original


def _replacement(*, expires_at: datetime | None = None) -> IssuedBrowserSession:
    return IssuedBrowserSession(
        REPLACEMENT_ID,
        REPLACEMENT_CSRF,
        NOW + timedelta(minutes=5) if expires_at is None else expires_at,
    )


def _rotate(
    port: BrowserSessionRotationStore,
    current_id: SessionId,
    replacement: IssuedBrowserSession,
) -> bool:
    return port.rotate_session(current_id, replacement)


def _with_active_source(now=lambda: NOW) -> InMemoryBrowserSessions:
    return InMemoryBrowserSessions(
        {SESSION_ID: BrowserSessionRecord(_session(), NOW + timedelta(minutes=1))},
        now=now,
    )


def test_rotation_makes_old_invalid_and_new_valid_atomically() -> None:
    sessions = _with_active_source()

    assert _rotate(sessions, SESSION_ID, _replacement()) is True
    # old and new are never simultaneously active-observable
    assert sessions.get_session(SESSION_ID) is None
    assert sessions.get_session(REPLACEMENT_ID) is not None


def test_rotation_keeps_source_principal_and_uses_new_csrf() -> None:
    principal = SessionPrincipal(UserId("user-1"))
    source = ResolvedBrowserSession(principal, "old-csrf-proof")
    sessions = InMemoryBrowserSessions(
        {SESSION_ID: BrowserSessionRecord(source, NOW + timedelta(minutes=1))},
        now=lambda: NOW,
    )

    assert _rotate(sessions, SESSION_ID, _replacement()) is True

    rotated = sessions.get_session(REPLACEMENT_ID)
    assert rotated is not None
    assert rotated.principal is principal
    assert rotated.expected_csrf_token == REPLACEMENT_CSRF
    assert rotated.expected_csrf_token != "old-csrf-proof"


def test_rotation_of_unknown_source_is_neutral_false() -> None:
    sessions = InMemoryBrowserSessions({}, now=lambda: NOW)

    assert _rotate(sessions, SESSION_ID, _replacement()) is False
    assert sessions.get_session(REPLACEMENT_ID) is None


def test_rotation_of_expired_source_is_neutral_false() -> None:
    sessions = InMemoryBrowserSessions(
        {SESSION_ID: BrowserSessionRecord(_session(), NOW)},
        now=lambda: NOW,
    )

    assert _rotate(sessions, SESSION_ID, _replacement()) is False
    assert sessions.get_session(REPLACEMENT_ID) is None


def test_rotation_of_revoked_source_is_neutral_false() -> None:
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

    assert _rotate(sessions, SESSION_ID, _replacement()) is False
    assert sessions.get_session(REPLACEMENT_ID) is None


def test_rotation_target_collision_leaves_both_records_unchanged() -> None:
    source = _session()
    existing_target = ResolvedBrowserSession(
        SessionPrincipal(UserId("user-2")),
        "existing-target-proof",
    )
    sessions = InMemoryBrowserSessions(
        {
            SESSION_ID: BrowserSessionRecord(source, NOW + timedelta(minutes=1)),
            REPLACEMENT_ID: BrowserSessionRecord(
                existing_target, NOW + timedelta(minutes=1)
            ),
        },
        now=lambda: NOW,
    )

    assert _rotate(sessions, SESSION_ID, _replacement()) is False
    # neither existing record changed
    assert sessions.get_session(SESSION_ID) is source
    assert sessions.get_session(REPLACEMENT_ID) is existing_target


def test_rotation_rejects_identical_current_and_replacement_id() -> None:
    source = _session()
    sessions = InMemoryBrowserSessions(
        {SESSION_ID: BrowserSessionRecord(source, NOW + timedelta(minutes=1))},
        now=lambda: NOW,
    )
    same_id = IssuedBrowserSession(
        SESSION_ID, REPLACEMENT_CSRF, NOW + timedelta(minutes=5)
    )

    assert _rotate(sessions, SESSION_ID, same_id) is False
    assert sessions.get_session(SESSION_ID) is source


def test_rotation_rejects_already_expired_replacement() -> None:
    source = _session()
    sessions = InMemoryBrowserSessions(
        {SESSION_ID: BrowserSessionRecord(source, NOW + timedelta(minutes=1))},
        now=lambda: NOW,
    )

    assert _rotate(sessions, SESSION_ID, _replacement(expires_at=NOW)) is False
    assert sessions.get_session(SESSION_ID) is source
    assert sessions.get_session(REPLACEMENT_ID) is None


def test_rotation_reads_injected_clock_at_most_once() -> None:
    clock_reads = 0

    def now() -> datetime:
        nonlocal clock_reads
        clock_reads += 1
        return NOW

    sessions = _with_active_source(now=now)

    assert _rotate(sessions, SESSION_ID, _replacement()) is True
    assert clock_reads == 1


def test_rotation_does_not_read_clock_without_time_check() -> None:
    reads: list[int] = []

    def now() -> datetime:
        reads.append(1)
        return NOW

    empty = InMemoryBrowserSessions({}, now=now)
    assert _rotate(empty, SESSION_ID, _replacement()) is False  # unknown source

    collision = InMemoryBrowserSessions(
        {
            SESSION_ID: BrowserSessionRecord(_session(), NOW + timedelta(minutes=1)),
            REPLACEMENT_ID: BrowserSessionRecord(
                _session(), NOW + timedelta(minutes=1)
            ),
        },
        now=now,
    )
    assert _rotate(collision, SESSION_ID, _replacement()) is False  # target taken

    same_id = IssuedBrowserSession(SESSION_ID, REPLACEMENT_CSRF, NOW + timedelta(minutes=5))
    identical = InMemoryBrowserSessions(
        {SESSION_ID: BrowserSessionRecord(_session(), NOW + timedelta(minutes=1))},
        now=now,
    )
    assert _rotate(identical, SESSION_ID, same_id) is False  # identical id

    assert reads == []


def test_rotation_is_available_through_rotation_store_port() -> None:
    sessions = _with_active_source()

    result = _rotate(sessions, SESSION_ID, _replacement())

    assert result is True
    assert isinstance(result, bool)
