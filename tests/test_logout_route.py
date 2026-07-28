from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from liquent_platform.application.session_lifecycle_errors import (
    SessionRevocationUnavailable,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.in_memory import InMemoryBrowserSessions
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.transport.http.app import create_app


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)
COOKIE = "opaque-session"
BOUND_CSRF = "bound-csrf"
LOGOUT_URL = "/v1/session/logout"


def _active_session() -> ResolvedBrowserSession:
    return ResolvedBrowserSession(SessionPrincipal(UserId("user-1")), BOUND_CSRF)


class RecordingLookup:
    def __init__(self, session: ResolvedBrowserSession | None = None) -> None:
        self._session = session
        self.calls: list[SessionId] = []

    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None:
        self.calls.append(session_id)
        return self._session


class RecordingRevocations:
    def __init__(self, *, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.calls: list[SessionId] = []

    def revoke_session(self, session_id: SessionId) -> None:
        self.calls.append(session_id)
        if self.unavailable:
            raise SessionRevocationUnavailable
        return None


def _client(lookup: object, revocations: object) -> TestClient:
    app = create_app(logout_sessions=lookup, logout_revocations=revocations)
    return TestClient(app)


def _set_cookie(response) -> str | None:
    return response.headers.get("set-cookie")


# --- 1. Missing cookie -----------------------------------------------------

def test_missing_cookie_is_neutral_cleared_204() -> None:
    lookup = RecordingLookup()
    revocations = RecordingRevocations()
    client = _client(lookup, revocations)

    response = client.post(LOGOUT_URL)

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert "liquent_session=" in (_set_cookie(response) or "")
    assert lookup.calls == []
    assert revocations.calls == []


# --- 2. Unknown / expired / revoked all collapse to the same 204 -----------

def test_unknown_session_is_neutral_cleared_204() -> None:
    lookup = RecordingLookup(session=None)
    revocations = RecordingRevocations()
    client = _client(lookup, revocations)
    client.cookies.set("liquent_session", COOKIE)

    response = client.post(LOGOUT_URL)

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert "liquent_session=" in (_set_cookie(response) or "")
    assert lookup.calls == [SessionId(COOKIE)]
    assert revocations.calls == []


def test_expired_session_is_neutral_cleared_204() -> None:
    sessions = InMemoryBrowserSessions(
        {SessionId(COOKIE): BrowserSessionRecord(_active_session(), NOW)},
        now=lambda: NOW,
    )
    revocations = RecordingRevocations()
    client = _client(sessions, revocations)
    client.cookies.set("liquent_session", COOKIE)

    response = client.post(LOGOUT_URL)

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert "liquent_session=" in (_set_cookie(response) or "")
    assert revocations.calls == []


def test_revoked_session_is_neutral_cleared_204() -> None:
    sessions = InMemoryBrowserSessions(
        {
            SessionId(COOKIE): BrowserSessionRecord(
                _active_session(), NOW + timedelta(minutes=1), revoked_at=NOW
            )
        },
        now=lambda: NOW,
    )
    revocations = RecordingRevocations()
    client = _client(sessions, revocations)
    client.cookies.set("liquent_session", COOKIE)

    response = client.post(LOGOUT_URL)

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert "liquent_session=" in (_set_cookie(response) or "")
    assert revocations.calls == []


# --- 3. Valid active session with missing/wrong CSRF -> 403, no clear -------

@pytest.mark.parametrize("headers", [{}, {"X-CSRF-Token": "wrong-proof"}])
def test_valid_session_without_valid_csrf_is_403_without_revoke_or_clear(
    headers: dict[str, str],
) -> None:
    lookup = RecordingLookup(session=_active_session())
    revocations = RecordingRevocations()
    client = _client(lookup, revocations)
    client.cookies.set("liquent_session", COOKIE)

    response = client.post(LOGOUT_URL, headers=headers)

    assert response.status_code == 403
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert _set_cookie(response) is None  # cookie not cleared
    assert revocations.calls == []


# --- 4. Valid active session with correct CSRF -> revoke then clear, 204 ----

def test_valid_session_with_csrf_revokes_once_then_clears_204() -> None:
    lookup = RecordingLookup(session=_active_session())
    revocations = RecordingRevocations()
    client = _client(lookup, revocations)
    client.cookies.set("liquent_session", COOKIE)

    response = client.post(LOGOUT_URL, headers={"X-CSRF-Token": BOUND_CSRF})

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert "liquent_session=" in (_set_cookie(response) or "")
    assert lookup.calls == [SessionId(COOKIE)]
    assert revocations.calls == [SessionId(COOKIE)]  # exactly once


# --- 5. Store / infrastructure error -> 500, no clear ----------------------

def test_store_error_is_500_without_clearing_cookie() -> None:
    lookup = RecordingLookup(session=_active_session())
    revocations = RecordingRevocations(unavailable=True)
    client = _client(lookup, revocations)
    client.cookies.set("liquent_session", COOKIE)

    response = client.post(LOGOUT_URL, headers={"X-CSRF-Token": BOUND_CSRF})

    assert response.status_code == 500
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert _set_cookie(response) is None  # cookie not cleared
    assert revocations.calls == [SessionId(COOKIE)]  # attempted once


# --- Dependency configuration ----------------------------------------------

def test_only_lookup_dependency_is_configuration_error() -> None:
    with pytest.raises(ValueError):
        create_app(logout_sessions=RecordingLookup())


def test_only_revocation_dependency_is_configuration_error() -> None:
    with pytest.raises(ValueError):
        create_app(logout_revocations=RecordingRevocations())


def test_logout_route_absent_without_dependencies() -> None:
    client = TestClient(create_app())

    response = client.post(LOGOUT_URL)

    assert response.status_code == 404
