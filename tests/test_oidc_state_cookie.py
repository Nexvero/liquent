import inspect
from datetime import UTC, datetime, timedelta
from http.cookies import Morsel, SimpleCookie

from fastapi import Response

from liquent_platform.transport.http.oidc_state_cookie import (
    OIDC_STATE_COOKIE_NAME,
    clear_oidc_state_cookie,
    set_oidc_state_cookie,
)


NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
LIFETIME = timedelta(minutes=10)
STATE = "generated-state-1"


def _morsel(response: Response) -> Morsel:
    """Parse the single Set-Cookie header so attributes compare semantically.

    Attribute order is an implementation detail of the cookie library and is
    deliberately not pinned.
    """

    headers = [
        value.decode("latin-1")
        for key, value in response.raw_headers
        if key == b"set-cookie"
    ]
    assert len(headers) == 1, f"expected exactly one Set-Cookie, got {len(headers)}"
    jar: SimpleCookie = SimpleCookie()
    jar.load(headers[0])
    assert list(jar) == [OIDC_STATE_COOKIE_NAME]
    return jar[OIDC_STATE_COOKIE_NAME]


def test_clearing_expires_the_binding_slot_and_forbids_caching() -> None:
    response = Response()

    assert clear_oidc_state_cookie(response) is None

    morsel = _morsel(response)
    assert morsel.key == OIDC_STATE_COOKIE_NAME == "__Host-liquent_oidc_state"
    assert morsel.value == ""
    assert morsel["max-age"] == "0"
    assert morsel["expires"] != ""
    assert morsel["path"] == "/"
    assert morsel["domain"] == ""  # host-only, as the __Host- prefix requires
    assert morsel["secure"] is True
    assert morsel["httponly"] is True
    # RFC 6265bis matches the SameSite value case-insensitively.
    assert morsel["samesite"].lower() == "lax"
    assert response.headers["cache-control"] == "no-store"


def test_clearing_takes_only_the_response_and_returns_none() -> None:
    signature = inspect.signature(clear_oidc_state_cookie)

    assert list(signature.parameters) == ["response"]
    assert signature.return_annotation is None


def test_setter_and_clearer_address_the_identical_slot() -> None:
    """Same name, path, and attributes — otherwise the deletion would miss."""

    written = Response()
    set_oidc_state_cookie(written, STATE, now=NOW, lifetime=LIFETIME)
    cleared = Response()
    clear_oidc_state_cookie(cleared)

    set_morsel, clear_morsel = _morsel(written), _morsel(cleared)
    assert set_morsel.value == STATE  # the setter keeps the state verbatim
    assert clear_morsel.key == set_morsel.key
    assert clear_morsel["path"] == set_morsel["path"] == "/"
    assert clear_morsel["domain"] == set_morsel["domain"] == ""
    assert clear_morsel["secure"] == set_morsel["secure"] is True
    assert clear_morsel["httponly"] == set_morsel["httponly"] is True
    assert clear_morsel["samesite"].lower() == set_morsel["samesite"].lower()
