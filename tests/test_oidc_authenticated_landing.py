from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import (
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.persistence.identity_errors import BrowserSessionStoreUnavailable
from liquent_platform.transport.http.app import create_app


class RecordingSessions:
    def __init__(self, result: ResolvedBrowserSession | None = None) -> None:
        self.result = result
        self.error: Exception | None = None
        self.calls: list[SessionId] = []

    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None:
        self.calls.append(session_id)
        if self.error is not None:
            raise self.error
        return self.result


def _client(sessions: RecordingSessions) -> TestClient:
    callback_dependencies: dict[str, Any] = {
        "oidc_callback_transactions": object(),
        "oidc_callback_verifier": object(),
        "oidc_callback_identities": object(),
        "oidc_callback_admissions": object(),
        "oidc_callback_sessions": object(),
        "oidc_callback_material": object(),
        "oidc_login_clock": lambda: datetime(2026, 9, 10, tzinfo=UTC),
        "oidc_session_lifetime": timedelta(hours=1),
        "oidc_callback_rejection": ValidatedInternalDestination("/login/rejected"),
        "oidc_callback_unavailable": ValidatedInternalDestination(
            "/login/unavailable"
        ),
        "logout_sessions": sessions,
        "logout_revocations": object(),
    }
    return TestClient(create_app(**callback_dependencies))


def _active_session() -> ResolvedBrowserSession:
    return ResolvedBrowserSession(
        principal=SessionPrincipal(UserId("internal-user")),
        expected_csrf_token="private-csrf",
    )


def _authenticated_client(sessions: RecordingSessions, value: str) -> TestClient:
    client = _client(sessions)
    client.cookies.set("liquent_session", value)
    return client


def test_active_session_receives_static_detail_free_landing() -> None:
    sessions = RecordingSessions(_active_session())
    response = _authenticated_client(sessions, "opaque-session").get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "Signed in to Liquent" in response.text
    assert "internal-user" not in response.text
    assert "private-csrf" not in response.text
    assert "<script" not in response.text
    assert "<form" not in response.text
    assert sessions.calls == [SessionId("opaque-session")]


def test_missing_session_redirects_to_login_without_lookup() -> None:
    sessions = RecordingSessions()
    response = _client(sessions).get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.content == b""
    assert response.headers.get("set-cookie") is None
    assert sessions.calls == []


def test_unknown_session_redirects_neutrally_and_clears_cookie() -> None:
    response = _authenticated_client(
        RecordingSessions(), "unknown-session"
    ).get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert "liquent_session=" in response.headers["set-cookie"]
    assert response.content == b""


def test_unavailable_lookup_redirects_without_clearing_cookie() -> None:
    sessions = RecordingSessions()
    sessions.error = BrowserSessionStoreUnavailable()
    response = _authenticated_client(
        sessions, "possibly-valid-session"
    ).get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login/unavailable"
    assert response.headers.get("set-cookie") is None
    assert response.content == b""


@pytest.mark.parametrize(
    "method",
    ["HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"],
)
def test_landing_rejects_every_non_get_method_without_lookup(method: str) -> None:
    sessions = RecordingSessions(_active_session())
    response = _authenticated_client(sessions, "opaque-session").request(method, "/")

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert response.headers["cache-control"] == "no-store"
    assert response.content == b""
    assert sessions.calls == []


def test_landing_rejects_query_without_lookup_or_reflection() -> None:
    sessions = RecordingSessions(_active_session())
    response = _authenticated_client(sessions, "opaque-session").get(
        "/?return=caller-value"
    )

    assert response.status_code == 400
    assert response.headers["cache-control"] == "no-store"
    assert response.content == b""
    assert "caller-value" not in response.text
    assert sessions.calls == []


def test_default_app_does_not_expose_landing() -> None:
    assert TestClient(create_app()).get("/").status_code == 404
