import inspect
from datetime import UTC, datetime, timedelta
from http.cookies import Morsel, SimpleCookie

import pytest
from fastapi import Response

from liquent_platform.transport.http.oidc_state_cookie import (
    OIDC_STATE_COOKIE_NAME,
    clear_oidc_state_cookie,
    set_oidc_state_cookie,
)


NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
LIFETIME = timedelta(minutes=10)
STATE = "generated-state-1"


def _set_cookie_headers(response: Response) -> list[str]:
    return [
        value.decode("latin-1")
        for key, value in response.raw_headers
        if key == b"set-cookie"
    ]


def _morsel(response: Response) -> Morsel:
    """Parse the Set-Cookie header so attributes are compared semantically.

    Attribute order in the header is an implementation detail of the cookie
    library; asserting on it would be fragile without testing anything real.
    """

    headers = _set_cookie_headers(response)
    assert len(headers) == 1, f"expected exactly one Set-Cookie, got {len(headers)}"
    jar: SimpleCookie = SimpleCookie()
    jar.load(headers[0])
    assert list(jar) == [OIDC_STATE_COOKIE_NAME]
    return jar[OIDC_STATE_COOKIE_NAME]


def _cleared() -> Response:
    response = Response()
    clear_oidc_state_cookie(response)
    return response


# --- 1. Return value -------------------------------------------------------

def test_clearing_returns_none() -> None:
    assert clear_oidc_state_cookie(Response()) is None


# --- 2. The exact same slot ------------------------------------------------

def test_cleared_cookie_uses_the_host_prefixed_binding_name() -> None:
    assert _morsel(_cleared()).key == "__Host-liquent_oidc_state"


def test_the_name_comes_from_the_shared_constant() -> None:
    assert OIDC_STATE_COOKIE_NAME == "__Host-liquent_oidc_state"
    assert _morsel(_cleared()).key == OIDC_STATE_COOKIE_NAME


# --- 3. Empty value, immediate expiry --------------------------------------

def test_cleared_cookie_has_an_empty_value() -> None:
    assert _morsel(_cleared()).value == ""


def test_cleared_cookie_expires_immediately() -> None:
    morsel = _morsel(_cleared())

    # Max-Age=0 is the unambiguous deletion signal; an expires attribute is
    # emitted alongside it for clients that ignore Max-Age.
    assert morsel["max-age"] == "0"
    assert morsel["expires"] != ""


# --- 4.-8. Transport attributes, compared semantically ---------------------

def test_cleared_cookie_keeps_the_root_path() -> None:
    assert _morsel(_cleared())["path"] == "/"


def test_cleared_cookie_is_secure() -> None:
    assert _morsel(_cleared())["secure"] is True


def test_cleared_cookie_is_http_only() -> None:
    assert _morsel(_cleared())["httponly"] is True


def test_cleared_cookie_keeps_samesite_lax() -> None:
    # RFC 6265bis matches the SameSite value case-insensitively.
    assert _morsel(_cleared())["samesite"].lower() == "lax"


def test_cleared_cookie_carries_no_domain() -> None:
    # Host-only, exactly as when set: the __Host- prefix forbids a Domain.
    assert _morsel(_cleared())["domain"] == ""
    assert "domain=" not in _set_cookie_headers(_cleared())[0].lower()


# --- 9. Caching ------------------------------------------------------------

def test_clearing_sets_cache_control_no_store() -> None:
    assert _cleared().headers["cache-control"] == "no-store"


# --- 10.-11. Signature boundary --------------------------------------------

def test_signature_has_only_response() -> None:
    assert list(inspect.signature(clear_oidc_state_cookie).parameters) == ["response"]


def test_return_annotation_is_none() -> None:
    assert inspect.signature(clear_oidc_state_cookie).return_annotation is None


@pytest.mark.parametrize(
    "name",
    ["now", "clock", "lifetime", "expires", "max_age", "state", "state_value", "value"],
)
def test_signature_has_no_clock_lifetime_or_state_parameter(name: str) -> None:
    assert name not in inspect.signature(clear_oidc_state_cookie).parameters


def test_clearing_needs_nothing_but_the_response() -> None:
    """No clock, no lifetime, no state value has to be available to call it."""

    response = Response()

    clear_oidc_state_cookie(response)

    assert _morsel(response).value == ""


# --- 12. One slot, and no existence oracle ---------------------------------

def test_clearing_writes_exactly_one_set_cookie_header() -> None:
    assert len(_set_cookie_headers(_cleared())) == 1


def test_clearing_looks_identical_regardless_of_any_prior_request_cookie() -> None:
    """The helper reads no request cookie, so it cannot reveal presence."""

    first = _cleared()
    second = _cleared()

    assert _set_cookie_headers(first)[0] == _set_cookie_headers(second)[0]


def test_clearing_does_not_touch_the_session_cookie() -> None:
    header = _set_cookie_headers(_cleared())[0]

    assert "liquent_session" not in header


# --- Setter regression, and the shared slot --------------------------------

def _was_set() -> Response:
    response = Response()
    set_oidc_state_cookie(response, STATE, now=NOW, lifetime=LIFETIME)
    return response


def test_setter_still_writes_the_same_slot_with_its_attributes() -> None:
    morsel = _morsel(_was_set())

    assert morsel.key == OIDC_STATE_COOKIE_NAME
    assert morsel.value == STATE
    assert morsel["path"] == "/"
    assert morsel["domain"] == ""
    assert morsel["secure"] is True
    assert morsel["httponly"] is True
    assert morsel["samesite"].lower() == "lax"


def test_setter_max_age_stays_bounded_by_the_lifetime() -> None:
    max_age = int(_morsel(_was_set())["max-age"])

    assert 0 < max_age <= LIFETIME.total_seconds()


def test_setter_and_clearer_address_the_identical_slot() -> None:
    """Same name, path, and absence of domain — otherwise deletion would miss."""

    written = _morsel(_was_set())
    cleared = _morsel(_cleared())

    assert cleared.key == written.key
    assert cleared["path"] == written["path"]
    assert cleared["domain"] == written["domain"] == ""
    assert cleared["secure"] == written["secure"]
    assert cleared["httponly"] == written["httponly"]
    assert cleared["samesite"].lower() == written["samesite"].lower()


def test_the_cleared_slot_no_longer_carries_the_state() -> None:
    """The setter's slot holds the state; the same slot, cleared, holds nothing."""

    assert _morsel(_was_set()).value == STATE
    assert _morsel(_cleared()).value == ""
    assert STATE not in _set_cookie_headers(_cleared())[0]
