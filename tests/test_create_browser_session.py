from datetime import UTC, datetime

import pytest

from liquent_platform.application.create_session import create_browser_session
from liquent_platform.application.session_lifecycle_errors import (
    SessionLifecycleConflict,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.ports import BrowserSessionCreationStore
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    IssuedBrowserSession,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)


EXPIRES_AT = datetime(2026, 7, 28, 13, tzinfo=UTC)


class StubCreationStore:
    def __init__(self, *, added: bool = True) -> None:
        self.added = added
        self.calls: list[tuple[SessionId, BrowserSessionRecord]] = []

    def add_session(
        self,
        session_id: SessionId,
        record: BrowserSessionRecord,
    ) -> bool:
        self.calls.append((session_id, record))
        return self.added


def _issued() -> IssuedBrowserSession:
    return IssuedBrowserSession(
        SessionId("opaque-session"),
        "private-csrf-proof",
        EXPIRES_AT,
    )


def _use_store(port: BrowserSessionCreationStore) -> bool:
    issued = _issued()
    record = BrowserSessionRecord(
        session=ResolvedBrowserSession(
            SessionPrincipal(UserId("user-1")),
            issued.csrf_token,
        ),
        expires_at=issued.expires_at,
    )
    return port.add_session(issued.session_id, record)


def test_creation_store_port_accepts_atomic_add_contract() -> None:
    store = StubCreationStore()

    assert _use_store(store) is True


def test_create_persists_bound_record_and_returns_issued_material() -> None:
    store = StubCreationStore()
    principal = SessionPrincipal(UserId("user-1"))
    issued = _issued()

    result = create_browser_session(store, principal, issued)

    assert result is issued
    assert len(store.calls) == 1
    session_id, record = store.calls[0]
    assert session_id == issued.session_id
    assert record.session.principal is principal
    assert record.session.expected_csrf_token == issued.csrf_token
    assert record.expires_at == issued.expires_at
    assert record.revoked_at is None


def test_create_reports_collision_as_neutral_conflict() -> None:
    store = StubCreationStore(added=False)

    with pytest.raises(SessionLifecycleConflict) as raised:
        create_browser_session(
            store,
            SessionPrincipal(UserId("user-1")),
            _issued(),
        )

    assert str(raised.value) == "session_lifecycle_conflict"
    assert len(store.calls) == 1
