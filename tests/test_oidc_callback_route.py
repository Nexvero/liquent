from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie
from typing import Any

import pytest
from fastapi.testclient import TestClient

from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
)
from liquent_platform.application.oidc_login_errors import (
    OidcLoginCompletionUnavailable,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.in_memory import InMemoryExternalIdentities
from liquent_platform.identity.oidc_login_transaction import (
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.oidc_verification import OidcVerificationUnavailable
from liquent_platform.identity.session import SessionId
from liquent_platform.transport.http import app as app_module
from liquent_platform.transport.http.app import create_app

CALLBACK_URL = "/v1/session/oidc/callback"
STATE = "state-value-1"
CODE = "authorization-code-1"
NOW = datetime(2026, 8, 10, 12, tzinfo=UTC)
SESSION_LIFETIME = timedelta(hours=8)
IDENTITY = ExternalIdentity(issuer="https://idp.example.test", subject="subject-1")
BOUND_USER = UserId("user-bound")
REJECTION = ValidatedInternalDestination("/login/failed")
UNAVAILABLE = ValidatedInternalDestination("/service/unavailable")


class Clock:
    def __init__(self, *moments: Any) -> None:
        self.moments = list(moments) or [NOW]
        self.calls = 0

    def __call__(self) -> Any:
        self.calls += 1
        moment = self.moments[min(self.calls - 1, len(self.moments) - 1)]
        if isinstance(moment, BaseException):
            raise moment
        return moment


class ClaimStore:
    def __init__(self, result: Any = "pending") -> None:
        self.result = result
        self.calls: list[Any] = []

    def claim_transaction(self, state: Any) -> Any:
        self.calls.append(state)
        if isinstance(self.result, BaseException):
            raise self.result
        if self.result != "pending":
            return self.result
        return PendingOidcLoginTransaction(
            expected_issuer="https://idp.example.test",
            expected_nonce="nonce-1",
            code_verifier="verifier-1",
            redirect_uri="https://app.example.test/v1/session/oidc/callback",
            created_at=NOW - timedelta(minutes=1),
            expires_at=NOW + timedelta(minutes=9),
            return_path=self.return_path,
        )

    return_path: str | None = None


class Verifier:
    def __init__(self, result: Any = IDENTITY) -> None:
        self.result = result
        self.calls: list[Any] = []

    def verify_authorization_code(self, verification: Any) -> Any:
        self.calls.append(verification)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class SessionStore:
    def __init__(self, result: Any = True) -> None:
        self.result = result
        self.calls: list[Any] = []

    def add_session(self, session_id: Any, record: Any) -> Any:
        self.calls.append((session_id, record))
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class Material:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def new_session_id(self) -> SessionId:
        self.calls.append("session_id")
        return SessionId("session-1")

    def new_csrf_token(self) -> str:
        self.calls.append("csrf_token")
        return "csrf-token-1"


def _dependencies(**overrides: Any) -> dict[str, Any]:
    identities = InMemoryExternalIdentities({}, {IDENTITY: BOUND_USER}, now=lambda: NOW)
    parts: dict[str, Any] = {
        "oidc_login_clock": Clock(),
        "oidc_callback_transactions": ClaimStore(),
        "oidc_callback_verifier": Verifier(),
        "oidc_callback_identities": identities,
        "oidc_callback_admissions": identities,
        "oidc_callback_sessions": SessionStore(),
        "oidc_callback_material": Material(),
        "oidc_session_lifetime": SESSION_LIFETIME,
        "oidc_callback_rejection": REJECTION,
        "oidc_callback_unavailable": UNAVAILABLE,
    }
    parts.update(overrides)
    return parts


def _call(
    query: str = f"state={STATE}&code={CODE}",
    cookie: str | None = STATE,
    **overrides: Any,
) -> tuple[Any, dict[str, Any]]:
    parts = _dependencies(**overrides)
    client = TestClient(create_app(**parts))
    if cookie is not None:
        client.cookies.set("__Host-liquent_oidc_state", cookie)
    suffix = f"?{query}" if query else ""
    return client.get(CALLBACK_URL + suffix, follow_redirects=False), parts


def _set_cookies(response: Any) -> dict[str, Any]:
    jar: dict[str, Any] = {}
    for header in response.headers.get_list("set-cookie"):
        parsed = SimpleCookie()
        parsed.load(header)
        jar.update(parsed)
    return jar


def _assert_privacy(response: Any) -> None:
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.content == b""
    assert "content-type" not in response.headers


# --- wiring -----------------------------------------------------------------


def test_the_callback_is_configured_independently_of_the_login_start() -> None:
    app = create_app(**_dependencies())

    assert CALLBACK_URL in {route.path for route in app.routes}
    assert "/v1/session/oidc/login" not in {route.path for route in app.routes}
    assert CALLBACK_URL not in {route.path for route in create_app().routes}


@pytest.mark.parametrize(
    "missing",
    [
        "oidc_callback_transactions",
        "oidc_callback_rejection",
        "oidc_login_clock",
    ],
)
def test_an_incomplete_callback_group_fails_at_app_build(missing: str) -> None:
    arguments = _dependencies()
    del arguments[missing]

    with pytest.raises(ValueError):
        create_app(**arguments)


@pytest.mark.parametrize(
    "lifetime",
    [timedelta(milliseconds=999), timedelta(0), timedelta(seconds=-1)],
    ids=["sub-second", "zero", "negative"],
)
def test_a_session_lifetime_below_one_whole_second_fails_at_app_build(
    lifetime: timedelta,
) -> None:
    with pytest.raises(ValueError) as raised:
        create_app(**_dependencies(oidc_session_lifetime=lifetime))

    assert str(lifetime) not in str(raised.value)


# --- success ----------------------------------------------------------------


def test_a_full_success_issues_the_session_and_clears_the_binding() -> None:
    response, parts = _call()

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert response.headers["x-csrf-token"] == "csrf-token-1"
    _assert_privacy(response)
    # Both slots survive in the same response; neither assignment overwrote the
    # other, and the binding cookie is expired rather than reset.
    cookies = _set_cookies(response)
    assert set(cookies) == {"liquent_session", "__Host-liquent_oidc_state"}
    assert cookies["liquent_session"].value == "session-1"
    assert cookies["__Host-liquent_oidc_state"]["max-age"] in ("0", 0)
    assert parts["oidc_callback_material"].calls == ["session_id", "csrf_token"]
    assert len(parts["oidc_callback_sessions"].calls) == 1


def test_a_stored_return_path_reaches_location_verbatim() -> None:
    store = ClaimStore()
    store.return_path = "/workspaces/w-1/research"

    response, _ = _call(oidc_callback_transactions=store)

    assert response.headers["location"] == "/workspaces/w-1/research"


# --- methods ----------------------------------------------------------------


@pytest.mark.parametrize(
    "method",
    ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"],
)
def test_every_other_method_is_an_empty_405_without_side_effects(method: str) -> None:
    parts = _dependencies()
    client = TestClient(create_app(**parts))

    response = client.request(method, CALLBACK_URL, follow_redirects=False)

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert response.headers.get("location") is None
    assert response.headers.get("set-cookie") is None
    _assert_privacy(response)
    assert parts["oidc_callback_transactions"].calls == []
    assert parts["oidc_login_clock"].calls == 0


# --- raw query gate ---------------------------------------------------------


# Three components, none over 4096 bytes, so only the total length decides.
_HEAD = f"state={STATE}&code=" + "c" * (4096 - len("code="))
_FILL = "&error_uri=" + "u" * (8192 - len(_HEAD) - len("&error_uri="))


@pytest.mark.parametrize(
    ("query", "accepted"),
    [
        (_HEAD + _FILL, True),
        (_HEAD + _FILL + "u", False),
        (f"state={STATE}&code={CODE}&a=1&b=2&c=3", False),
        (f"state={STATE}&code=" + "c" * (4097 - len("code=")), False),
        ("&&&&" + f"state={STATE}", False),
        ("", False),
    ],
    ids=["8192", "8193", "five-components", "component-4097", "empty-components", "no-query"],
)
def test_the_raw_gate_runs_before_any_cookie_or_dependency(
    query: str, accepted: bool
) -> None:
    response, parts = _call(query=query)

    assert response.status_code == 303
    if accepted:
        # Passed the gate, then refused later for its own reason.
        assert parts["oidc_callback_transactions"].calls != []
    else:
        assert response.headers["location"] == REJECTION.value
        assert response.headers.get("set-cookie") is None
        assert parts["oidc_callback_transactions"].calls == []
        assert parts["oidc_login_clock"].calls == 0


# --- pre-match business rejections -----------------------------------------


@pytest.mark.parametrize(
    ("query", "cookie"),
    [
        (f"code={CODE}", STATE),
        (f"state=&code={CODE}", STATE),
        (f"state={STATE}&state=other&code={CODE}", STATE),
        (f"state={STATE}&code={CODE}", None),
        (f"state={STATE}&code={CODE}", "a-newer-login-state"),
    ],
    ids=["no-state", "empty-state", "duplicate-state", "no-cookie", "mismatch"],
)
def test_a_pre_match_rejection_never_claims_and_never_clears(
    query: str, cookie: str | None
) -> None:
    response, parts = _call(query=query, cookie=cookie)

    assert response.status_code == 303
    assert response.headers["location"] == REJECTION.value
    assert response.headers.get("set-cookie") is None
    _assert_privacy(response)
    assert parts["oidc_callback_transactions"].calls == []
    assert parts["oidc_callback_verifier"].calls == []
    assert parts["oidc_callback_sessions"].calls == []
    assert parts["oidc_login_clock"].calls == 0


# --- post-match outcomes ----------------------------------------------------


@pytest.mark.parametrize(
    ("query", "overrides", "location"),
    [
        (f"state={STATE}&code={CODE}&unknown=1", {}, REJECTION.value),
        (f"state={STATE}&code={CODE}&error=denied", {}, REJECTION.value),
        (f"state={STATE}&error=access_denied", {}, REJECTION.value),
        (
            f"state={STATE}&code={CODE}",
            {"oidc_callback_transactions": ClaimStore(None)},
            REJECTION.value,
        ),
        (
            f"state={STATE}&code={CODE}",
            {"oidc_callback_verifier": Verifier(None)},
            REJECTION.value,
        ),
        (
            f"state={STATE}&code={CODE}",
            {"oidc_callback_verifier": Verifier(OidcVerificationUnavailable())},
            UNAVAILABLE.value,
        ),
        (
            f"state={STATE}&code={CODE}",
            {"oidc_callback_sessions": SessionStore(OidcLoginCompletionUnavailable())},
            UNAVAILABLE.value,
        ),
    ],
    ids=[
        "unknown-parameter",
        "code-and-error",
        "provider-error",
        "claim-refused",
        "verifier-refused",
        "verification-unavailable",
        "completion-unavailable",
    ],
)
def test_every_post_match_outcome_clears_and_issues_no_session(
    query: str, overrides: dict[str, Any], location: str
) -> None:
    response, _ = _call(query=query, **overrides)

    assert response.status_code == 303
    assert response.headers["location"] == location
    assert set(_set_cookies(response)) == {"__Host-liquent_oidc_state"}
    assert "x-csrf-token" not in response.headers
    _assert_privacy(response)


def test_an_invalid_stored_return_path_is_refused_without_a_default_fallback() -> None:
    store = ClaimStore()
    store.return_path = "//evil.test"
    sessions = SessionStore()

    response, _ = _call(oidc_callback_transactions=store, oidc_callback_sessions=sessions)

    assert response.headers["location"] == REJECTION.value
    assert "x-csrf-token" not in response.headers
    assert set(_set_cookies(response)) == {"__Host-liquent_oidc_state"}
    # The server-side session was stored before the destination was refused and
    # is deliberately not rolled back.
    assert len(sessions.calls) == 1


# --- unexpected faults ------------------------------------------------------


@pytest.mark.parametrize(
    ("pre_match", "overrides"),
    [
        (True, {}),
        (False, {"oidc_callback_transactions": ClaimStore(RuntimeError("CLAIM-DETAIL"))}),
        (False, {"oidc_callback_verifier": Verifier(RuntimeError("VERIFY-DETAIL"))}),
        (False, {"oidc_callback_sessions": SessionStore(RuntimeError("STORE-DETAIL"))}),
    ],
    ids=["pre-match", "claim", "verify", "session-store"],
)
def test_an_unexpected_fault_follows_the_match_state_and_stays_detail_free(
    monkeypatch: pytest.MonkeyPatch, pre_match: bool, overrides: dict[str, Any]
) -> None:
    if pre_match:
        # No injected collaborator runs before the match, so the only honest way
        # to reach that branch is to break the route's own pre-match step.
        def _explode(_: Any) -> Any:
            raise RuntimeError("PRE-MATCH-DETAIL")

        monkeypatch.setattr(app_module, "_single_callback_state", _explode)

    response, parts = _call(**overrides)

    assert response.status_code == 303
    assert response.headers["location"] == UNAVAILABLE.value
    _assert_privacy(response)
    assert "x-csrf-token" not in response.headers
    if pre_match:
        # The single cookie slot may hold a newer login's binding.
        assert response.headers.get("set-cookie") is None
        assert parts["oidc_callback_transactions"].calls == []
        assert parts["oidc_login_clock"].calls == 0
    else:
        assert set(_set_cookies(response)) == {"__Host-liquent_oidc_state"}
    for secret in ("DETAIL", STATE, CODE, "session-1", "csrf-token-1"):
        assert secret not in response.headers["location"]


# --- clock ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("clock", "expected_calls", "location"),
    [
        (Clock(NOW, NOW), 2, "/"),
        (Clock(NOW, NOW.replace(tzinfo=None)), 2, UNAVAILABLE.value),
        (Clock(NOW, NOW + SESSION_LIFETIME), 2, UNAVAILABLE.value),
    ],
    ids=["success", "naive-second-read", "already-expired"],
)
def test_the_clock_is_read_exactly_twice_and_only_after_completion(
    clock: Clock, expected_calls: int, location: str
) -> None:
    response, _ = _call(oidc_login_clock=clock)

    assert clock.calls == expected_calls
    assert response.headers["location"] == location
    if location != "/":
        # The session was stored before the unusable instant; no rollback, no
        # second issuance, and no client-side session output.
        assert set(_set_cookies(response)) == {"__Host-liquent_oidc_state"}
        assert "x-csrf-token" not in response.headers


def test_a_base_exception_is_not_translated_into_a_response() -> None:
    cancel = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt) as raised:
        _call(oidc_callback_transactions=ClaimStore(cancel))

    assert raised.value is cancel
