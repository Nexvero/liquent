from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Response

from liquent_platform.identity.session import IssuedBrowserSession, SessionId
from liquent_platform.transport.http.session_cookie import (
    CSRF_RESPONSE_HEADER_NAME,
    clear_session_cookie,
    set_issued_session,
    set_session_cookie,
)


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


def issued(*, expires_at: datetime) -> IssuedBrowserSession:
    return IssuedBrowserSession(
        SessionId("opaque-session"),
        "private-csrf-proof",
        expires_at,
    )


def test_set_session_cookie_applies_secure_host_only_contract() -> None:
    response = Response()

    set_session_cookie(response, issued(expires_at=NOW + timedelta(hours=1)), now=NOW)

    cookie = response.headers["set-cookie"]
    assert cookie.startswith("liquent_session=opaque-session;")
    assert "HttpOnly" in cookie
    assert "Max-Age=3600" in cookie
    assert "Path=/" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" in cookie
    assert "Domain=" not in cookie
    assert response.headers["cache-control"] == "no-store"
    assert response.body == b""


def test_set_session_cookie_floors_browser_lifetime() -> None:
    response = Response()

    set_session_cookie(
        response,
        issued(expires_at=NOW + timedelta(seconds=1, microseconds=900_000)),
        now=NOW,
    )

    assert "Max-Age=1" in response.headers["set-cookie"]


@pytest.mark.parametrize(
    "now",
    [NOW, NOW + timedelta(seconds=1)],
)
def test_set_session_cookie_rejects_non_future_expiry(now: datetime) -> None:
    response = Response()

    with pytest.raises(ValueError, match="expiry must be in the future"):
        set_session_cookie(response, issued(expires_at=NOW), now=now)

    assert "set-cookie" not in response.headers


def test_set_session_cookie_rejects_naive_clock() -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        set_session_cookie(
            Response(),
            issued(expires_at=NOW + timedelta(hours=1)),
            now=datetime(2026, 7, 28, 12),
        )


def test_clear_session_cookie_expires_same_host_only_cookie() -> None:
    response = Response()

    clear_session_cookie(response)

    cookie = response.headers["set-cookie"]
    assert cookie.startswith('liquent_session="";')
    assert "HttpOnly" in cookie
    assert "Max-Age=0" in cookie
    assert "Path=/" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" in cookie
    assert "Domain=" not in cookie
    assert response.headers["cache-control"] == "no-store"


def test_set_issued_session_uses_separate_cookie_and_csrf_header() -> None:
    response = Response()
    material = issued(expires_at=NOW + timedelta(hours=1))

    set_issued_session(response, material, now=NOW)

    assert "liquent_session=opaque-session" in response.headers["set-cookie"]
    assert "private-csrf-proof" not in response.headers["set-cookie"]
    assert response.headers[CSRF_RESPONSE_HEADER_NAME] == "private-csrf-proof"
    assert response.headers["cache-control"] == "no-store"
    assert response.body == b""


@pytest.mark.parametrize("csrf_token", ["contains space", "line\nbreak", "tökén"])
def test_set_issued_session_rejects_unsafe_csrf_header_before_mutation(
    csrf_token: str,
) -> None:
    response = Response()
    material = IssuedBrowserSession(
        SessionId("opaque-session"),
        csrf_token,
        NOW + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="HTTP-header-safe ASCII"):
        set_issued_session(response, material, now=NOW)

    assert "set-cookie" not in response.headers
    assert CSRF_RESPONSE_HEADER_NAME not in response.headers


def test_set_issued_session_rejects_expired_material_before_mutation() -> None:
    response = Response()

    with pytest.raises(ValueError, match="expiry must be in the future"):
        set_issued_session(response, issued(expires_at=NOW), now=NOW)

    assert "set-cookie" not in response.headers
    assert CSRF_RESPONSE_HEADER_NAME not in response.headers
