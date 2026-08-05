from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest
from fastapi.testclient import TestClient

import liquent_platform.application.prepare_oidc_login_authorization as use_case_module
from liquent_platform.application.build_oidc_authorization_request import (
    OidcAuthorizationRequest,
)
from liquent_platform.application.oidc_login_errors import (
    OidcLoginStartConflict,
    OidcLoginUnavailable,
)
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_login_material import OidcLoginMaterial
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.transport.http.app import create_app


LOGIN_URL = "/v1/session/oidc/login"
COOKIE_NAME = "__Host-liquent_oidc_state"

NOW = datetime(2026, 8, 4, 12, tzinfo=UTC)
LIFETIME = timedelta(minutes=10)
ORIGIN = "https://app.liquent.test"
OTHER_ORIGIN = "https://evil.example.test"

ISSUER = "https://idp.example.test"
ENDPOINT = "https://idp.example.test/authorize"
CLIENT_ID = "liquent-control-plane"
REDIRECT_URI = "https://app.liquent.test/v1/session/oidc/callback"
SCOPES = ("openid", "email")

STATE = "generated-state"
NONCE = "generated-nonce"
VERIFIER = "generated-verifier"
CHALLENGE = "generated-challenge"

SAME_ORIGIN_HEADERS = {"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"}


def _configuration() -> TrustedOidcClientConfiguration:
    return TrustedOidcClientConfiguration(
        issuer=ISSUER,
        authorization_endpoint=ENDPOINT,
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scopes=SCOPES,
    )


# --- Focused doubles --------------------------------------------------------


class RecordingLookup:
    def __init__(
        self,
        configuration: TrustedOidcClientConfiguration | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._configuration = configuration
        self._error = error
        self.calls = 0

    def get_active_configuration(self) -> TrustedOidcClientConfiguration | None:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._configuration


class RecordingStore:
    def __init__(
        self, *, added: bool = True, error: Exception | None = None
    ) -> None:
        self._added = added
        self._error = error
        self.calls: list[tuple[OidcLoginState, PendingOidcLoginTransaction]] = []

    def add_transaction(
        self,
        state: OidcLoginState,
        transaction: PendingOidcLoginTransaction,
    ) -> bool:
        self.calls.append((state, transaction))
        if self._error is not None:
            raise self._error
        return self._added


class RecordingGenerator:
    """Hands out a predictable state, optionally a different one per call."""

    def __init__(
        self,
        states: tuple[str, ...] = (STATE,),
        *,
        error: Exception | None = None,
    ) -> None:
        self._states = states
        self._error = error
        self.calls = 0

    def new_login_material(self) -> OidcLoginMaterial:
        self.calls += 1
        if self._error is not None:
            raise self._error
        state = self._states[min(self.calls - 1, len(self._states) - 1)]
        return OidcLoginMaterial(state, NONCE, VERIFIER, CHALLENGE)


class RecordingClock:
    def __init__(self, now: datetime = NOW) -> None:
        self._now = now
        self.calls = 0

    def __call__(self) -> datetime:
        self.calls += 1
        return self._now


# --- App / client helpers ---------------------------------------------------


def _app(
    lookup: Any = None,
    store: Any = None,
    generator: Any = None,
    clock: Any = None,
    **overrides: Any,
) -> Any:
    arguments: dict[str, Any] = {
        "oidc_login_configurations": lookup or RecordingLookup(_configuration()),
        "oidc_login_transactions": store or RecordingStore(),
        "oidc_login_material": generator or RecordingGenerator(),
        "oidc_login_clock": clock or RecordingClock(),
        "oidc_login_lifetime": LIFETIME,
        "oidc_login_origin": ORIGIN,
    }
    arguments.update(overrides)
    return create_app(**arguments)


def _client(*args: Any, **overrides: Any) -> TestClient:
    return TestClient(_app(*args, **overrides))


def _post(client: TestClient, **kwargs: Any):
    kwargs.setdefault("headers", SAME_ORIGIN_HEADERS)
    return client.post(LOGIN_URL, follow_redirects=False, **kwargs)


def _cookie(response: Any) -> SimpleCookie:
    raw = response.headers.get("set-cookie")
    assert raw is not None, "expected a Set-Cookie header"
    jar: SimpleCookie = SimpleCookie()
    jar.load(raw)
    return jar


def _assert_no_side_effects(response: Any, *args: Any) -> None:
    """A rejection stores nothing, sets nothing, and redirects nowhere."""

    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert response.headers.get("set-cookie") is None
    assert response.headers.get("location") is None
    assert "retry-after" not in response.headers
    for recorder in args:
        if isinstance(recorder, RecordingStore):
            assert recorder.calls == []
        else:
            assert recorder.calls == 0


# --- 1. Route presence and dependency boundary ------------------------------


def test_default_app_has_no_login_start_route() -> None:
    client = TestClient(create_app())

    response = client.post(LOGIN_URL, follow_redirects=False)

    assert response.status_code == 404


def test_full_injection_activates_the_route() -> None:
    client = _client()

    response = _post(client)

    assert response.status_code == 303


DEPENDENCY_NAMES = (
    "oidc_login_configurations",
    "oidc_login_transactions",
    "oidc_login_material",
    "oidc_login_clock",
    "oidc_login_lifetime",
    "oidc_login_origin",
)


def _complete_dependencies() -> dict[str, Any]:
    return {
        "oidc_login_configurations": RecordingLookup(_configuration()),
        "oidc_login_transactions": RecordingStore(),
        "oidc_login_material": RecordingGenerator(),
        "oidc_login_clock": RecordingClock(),
        "oidc_login_lifetime": LIFETIME,
        "oidc_login_origin": ORIGIN,
    }


@pytest.mark.parametrize("missing", DEPENDENCY_NAMES)
def test_one_missing_dependency_is_a_configuration_error(missing: str) -> None:
    arguments = _complete_dependencies()
    del arguments[missing]

    with pytest.raises(ValueError):
        create_app(**arguments)


@pytest.mark.parametrize("present", DEPENDENCY_NAMES)
def test_one_lonely_dependency_is_a_configuration_error(present: str) -> None:
    arguments = {present: _complete_dependencies()[present]}

    with pytest.raises(ValueError):
        create_app(**arguments)


@pytest.mark.parametrize(
    "lifetime", [timedelta(0), timedelta(seconds=-1), timedelta(minutes=-10)]
)
def test_non_positive_lifetime_is_a_configuration_error(
    lifetime: timedelta,
) -> None:
    with pytest.raises(ValueError):
        _app(oidc_login_lifetime=lifetime)


@pytest.mark.parametrize(
    "lifetime",
    [
        timedelta(milliseconds=1),
        timedelta(milliseconds=500),
        timedelta(milliseconds=999),
        timedelta(microseconds=1),
        timedelta(seconds=-0.5),  # truncates toward zero, not away from it
    ],
)
def test_a_sub_second_lifetime_is_a_configuration_error(
    lifetime: timedelta,
) -> None:
    """Max-Age would truncate to 0, which a browser expires immediately."""

    with pytest.raises(ValueError):
        _app(oidc_login_lifetime=lifetime)


@pytest.mark.parametrize(
    "lifetime",
    [
        timedelta(seconds=1),
        timedelta(seconds=1, milliseconds=500),
        timedelta(minutes=10),
        timedelta(hours=1),
    ],
)
def test_whole_second_lifetimes_keep_working_and_never_set_max_age_zero(
    lifetime: timedelta,
) -> None:
    client = TestClient(_app(oidc_login_lifetime=lifetime))

    response = _post(client)

    assert response.status_code == 303
    max_age = int(_cookie(response)[COOKIE_NAME]["max-age"])
    assert max_age >= 1
    assert max_age <= lifetime.total_seconds()


@pytest.mark.parametrize(
    "origin",
    [
        "",
        " ",
        " https://app.liquent.test",
        "https://app.liquent.test ",
        "https://a.test,https://b.test",
        "https://a.test https://b.test",
        "https://a.test\thttps://b.test",
    ],
)
def test_empty_or_multi_valued_origin_is_a_configuration_error(
    origin: str,
) -> None:
    with pytest.raises(ValueError):
        _app(oidc_login_origin=origin)


@pytest.mark.parametrize(
    "origin",
    [
        "garbage",
        "liquent.example",
        "//liquent.example",
        "http://liquent.example",  # scheme must be https
        "ftp://liquent.example",
        "HTTPS://liquent.example",  # the parser lowercases; the raw value stays
        "https://",  # no host
        "https://liquent.example/",  # a bare slash is still a path
        "https://liquent.example/path",
        "https://liquent.example/path/",
        "https://user@liquent.example",  # userinfo
        "https://user:secret@liquent.example",
        "https://@liquent.example",  # empty userinfo
        "https://liquent.example?x=1",  # query
        "https://liquent.example?",  # empty query separator
        "https://liquent.example#fragment",
        "https://liquent.example#",  # empty fragment separator
        "https://liquent.example:99999",  # port out of range
        "https://liquent.example:-1",
        "https://liquent.example:abc",  # port not an integer
        "https://liquent.example:",  # empty port
        "https://liquent.example:0",  # never a real listener
        "https://liquent.example:8443/",  # port plus path
        "https://liquent.example\nhttps://evil.test",  # urlsplit would strip \n
        "https://liquent.example\x7f",
    ],
)
def test_a_non_origin_shaped_value_is_a_configuration_error(origin: str) -> None:
    with pytest.raises(ValueError):
        _app(oidc_login_origin=origin)


@pytest.mark.parametrize(
    "origin",
    [
        "https://liquent.example",
        "https://liquent.example:8443",
        "https://app.liquent.test",
        "https://liquent.example:443",  # a default port is neither added nor removed
        "https://[::1]:8443",
        "https://localhost:8443",
    ],
)
def test_an_origin_shaped_value_is_accepted_verbatim(origin: str) -> None:
    client = TestClient(_app(oidc_login_origin=origin))

    response = client.post(
        LOGIN_URL,
        headers={"Origin": origin, "Sec-Fetch-Site": "same-origin"},
        follow_redirects=False,
    )

    assert response.status_code == 303


def test_the_origin_rejection_message_never_echoes_the_value() -> None:
    secret_looking = "https://internal-admin.liquent.example/path"

    with pytest.raises(ValueError) as raised:
        _app(oidc_login_origin=secret_looking)

    assert "internal-admin" not in str(raised.value)


def test_an_accepted_origin_is_not_normalized_before_the_comparison() -> None:
    """A configured default port stays required; the browser must send it too."""

    client = TestClient(_app(oidc_login_origin="https://liquent.example:443"))

    response = client.post(
        LOGIN_URL,
        headers={"Origin": "https://liquent.example"},
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_unrelated_routes_stay_reachable_without_oidc_dependencies() -> None:
    client = TestClient(create_app())

    assert client.get("/health/live").status_code == 200


# --- 2. Success response ----------------------------------------------------


def _expected_url() -> str:
    return (
        f"{ENDPOINT}?response_type=code&response_mode=query"
        f"&client_id={CLIENT_ID}"
        "&redirect_uri=https%3A%2F%2Fapp.liquent.test%2Fv1%2Fsession%2Foidc"
        "%2Fcallback"
        "&scope=openid+email"
        f"&state={STATE}&nonce={NONCE}"
        f"&code_challenge={CHALLENGE}&code_challenge_method=S256"
    )


def test_success_is_an_empty_303_with_the_authorization_url_in_location() -> None:
    client = _client()

    response = _post(client)

    assert response.status_code == 303
    assert response.content == b""
    assert response.headers["location"] == _expected_url()


def test_success_carries_the_exact_cache_and_referrer_headers() -> None:
    client = _client()

    response = _post(client)

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_success_body_has_no_authorization_url_and_no_content_type() -> None:
    client = _client()

    response = _post(client)

    assert response.content == b""
    assert response.headers.get("content-type") is None
    assert ENDPOINT not in response.text


# --- 3. Binding cookie ------------------------------------------------------


def test_cookie_uses_the_host_prefixed_binding_name_and_the_use_case_state() -> None:
    client = _client()

    response = _post(client)

    jar = _cookie(response)
    assert list(jar) == [COOKIE_NAME]
    assert jar[COOKIE_NAME].value == STATE


def test_cookie_attributes_match_the_host_prefix_contract() -> None:
    client = _client()

    response = _post(client)

    morsel = _cookie(response)[COOKIE_NAME]
    assert morsel["path"] == "/"
    assert morsel["domain"] == ""  # no Domain: host-only, as __Host- requires
    assert morsel["secure"] is True
    assert morsel["httponly"] is True
    # RFC 6265bis matches the SameSite value case-insensitively.
    assert morsel["samesite"].lower() == "lax"


def test_cookie_max_age_does_not_exceed_the_transaction_lifetime() -> None:
    client = _client()

    response = _post(client)

    max_age = int(_cookie(response)[COOKIE_NAME]["max-age"])
    assert 0 < max_age <= LIFETIME.total_seconds()


def test_cookie_expires_matches_the_same_now_plus_the_lifetime() -> None:
    clock = RecordingClock()
    client = _client(clock=clock)

    response = _post(client)

    expires = _cookie(response)[COOKIE_NAME]["expires"]
    assert expires == "Tue, 04 Aug 2026 12:10:00 GMT"


def test_a_non_utc_aware_clock_still_yields_the_same_instant() -> None:
    berlin_now = NOW.astimezone(timezone(timedelta(hours=2)))
    client = _client(clock=RecordingClock(berlin_now))

    response = _post(client)

    assert response.status_code == 303
    assert _cookie(response)[COOKIE_NAME]["expires"] == "Tue, 04 Aug 2026 12:10:00 GMT"


def test_success_does_not_touch_the_existing_session_cookie() -> None:
    client = _client()
    client.cookies.set("liquent_session", "unrelated-session")

    response = _post(client)

    assert "liquent_session" not in (response.headers.get("set-cookie") or "")


# --- 4. The state never comes from the authorization URL --------------------


@pytest.mark.parametrize(
    "forged_url",
    [
        f"{ENDPOINT}?state=url-state-does-not-match",
        f"{ENDPOINT}?state=",
        f"{ENDPOINT}?nonce={NONCE}",  # no state parameter at all
        ENDPOINT,
    ],
)
def test_cookie_state_survives_an_authorization_url_with_a_foreign_state(
    monkeypatch: pytest.MonkeyPatch, forged_url: str
) -> None:
    monkeypatch.setattr(
        use_case_module,
        "build_oidc_authorization_request",
        lambda configuration, started: OidcAuthorizationRequest(forged_url),
    )
    client = _client()

    response = _post(client)

    assert response.status_code == 303
    assert response.headers["location"] == forged_url
    # Parsed from the URL the cookie would be wrong or missing; it is neither.
    assert _cookie(response)[COOKIE_NAME].value == STATE
    url_state = dict(parse_qsl(urlsplit(forged_url).query, keep_blank_values=True))
    assert url_state.get("state") != STATE


def test_cookie_state_equals_the_stored_transaction_key() -> None:
    store = RecordingStore()
    client = _client(store=store)

    response = _post(client)

    stored_state, _ = store.calls[0]
    assert _cookie(response)[COOKIE_NAME].value == stored_state.value


# --- 5. Exactly-once behaviour and the fixed use-case arguments -------------


def test_clock_lookup_generator_and_store_run_exactly_once() -> None:
    lookup = RecordingLookup(_configuration())
    store = RecordingStore()
    generator = RecordingGenerator()
    clock = RecordingClock()
    client = _client(lookup, store, generator, clock)

    response = _post(client)

    assert response.status_code == 303
    assert clock.calls == 1
    assert lookup.calls == 1
    assert generator.calls == 1
    assert len(store.calls) == 1


def test_the_single_clock_reading_bounds_the_stored_transaction() -> None:
    store = RecordingStore()
    client = _client(store=store)

    _post(client)

    _, transaction = store.calls[0]
    assert transaction.created_at == NOW
    assert transaction.expires_at == NOW + LIFETIME


def test_no_admission_id_and_no_return_path_reach_the_transaction() -> None:
    store = RecordingStore()
    client = _client(store=store)

    _post(client)

    _, transaction = store.calls[0]
    assert transaction.admission_id is None
    assert transaction.return_path is None


@pytest.mark.parametrize(
    "smuggled",
    [
        {"params": {"admission_id": "admission-1"}},
        {"params": {"return_path": "/somewhere"}},
        {"data": {"admission_id": "admission-1"}},
    ],
)
def test_admission_and_return_path_cannot_be_smuggled_in(
    smuggled: dict[str, Any],
) -> None:
    store = RecordingStore()
    generator = RecordingGenerator()
    clock = RecordingClock()
    client = _client(store=store, generator=generator, clock=clock)

    response = _post(client, **smuggled)

    assert response.status_code == 400
    _assert_no_side_effects(response, store, generator, clock)


# --- 6. last-start-wins -----------------------------------------------------


def test_a_second_successful_start_overwrites_the_single_cookie_slot() -> None:
    generator = RecordingGenerator(("first-state", "second-state"))
    store = RecordingStore()
    client = _client(store=store, generator=generator)

    first = _post(client)
    second = _post(client)

    assert _cookie(first)[COOKIE_NAME].value == "first-state"
    assert _cookie(second)[COOKIE_NAME].value == "second-state"
    assert list(_cookie(second)) == [COOKIE_NAME]  # one slot, same name
    # Both pending records stay server-side; the older one expires fail-closed.
    assert [state.value for state, _ in store.calls] == [
        "first-state",
        "second-state",
    ]
    assert client.cookies[COOKIE_NAME] == "second-state"


# --- 7. Input boundary: no query, no body -----------------------------------


@pytest.mark.parametrize(
    "sent",
    [
        {"params": {"issuer": ISSUER}},
        {"params": {"provider": "acme"}},
        {"params": {"": ""}},
        {"data": {"prompt": "login"}},
        {"content": b"x"},
        {"json": {"login_hint": "someone@example.test"}},
    ],
)
def test_a_non_empty_query_or_body_is_a_neutral_400(sent: dict[str, Any]) -> None:
    lookup = RecordingLookup(_configuration())
    store = RecordingStore()
    generator = RecordingGenerator()
    clock = RecordingClock()
    client = _client(lookup, store, generator, clock)

    response = _post(client, **sent)

    assert response.status_code == 400
    _assert_no_side_effects(response, lookup, store, generator, clock)


def test_a_bare_question_mark_is_still_an_empty_query() -> None:
    client = _client()

    response = client.post(
        f"{LOGIN_URL}?", headers=SAME_ORIGIN_HEADERS, follow_redirects=False
    )

    assert response.status_code == 303


def test_input_rejection_wins_over_origin_rejection() -> None:
    clock = RecordingClock()
    client = _client(clock=clock)

    response = client.post(
        LOGIN_URL,
        params={"issuer": ISSUER},
        headers={"Origin": OTHER_ORIGIN},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert clock.calls == 0


# --- 8. Origin and Sec-Fetch-Site boundary ----------------------------------


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "null"},
        {"Origin": OTHER_ORIGIN},
        {"Origin": "http://app.liquent.test"},  # scheme differs
        {"Origin": "https://app.liquent.test:8443"},  # port differs
        {"Origin": "https://app.liquent.test/"},  # trailing slash differs
        {"Origin": "https://APP.liquent.test"},  # case differs, no normalization
        {"Referer": f"{ORIGIN}/login"},  # Referer is no substitute
    ],
)
def test_missing_null_or_foreign_origin_is_a_neutral_403(
    headers: dict[str, str],
) -> None:
    lookup = RecordingLookup(_configuration())
    store = RecordingStore()
    generator = RecordingGenerator()
    clock = RecordingClock()
    client = _client(lookup, store, generator, clock)

    response = client.post(LOGIN_URL, headers=headers, follow_redirects=False)

    assert response.status_code == 403
    _assert_no_side_effects(response, lookup, store, generator, clock)


@pytest.mark.parametrize(
    "fetch_site",
    ["cross-site", "same-site", "none", "", "Same-Origin", "unknown", "origin"],
)
def test_any_fetch_site_other_than_same_origin_is_a_neutral_403(
    fetch_site: str,
) -> None:
    lookup = RecordingLookup(_configuration())
    store = RecordingStore()
    generator = RecordingGenerator()
    clock = RecordingClock()
    client = _client(lookup, store, generator, clock)

    response = client.post(
        LOGIN_URL,
        headers={"Origin": ORIGIN, "Sec-Fetch-Site": fetch_site},
        follow_redirects=False,
    )

    assert response.status_code == 403
    _assert_no_side_effects(response, lookup, store, generator, clock)


def test_an_absent_fetch_site_header_is_accepted_with_a_matching_origin() -> None:
    client = _client()

    response = client.post(
        LOGIN_URL, headers={"Origin": ORIGIN}, follow_redirects=False
    )

    assert response.status_code == 303


def test_a_rejection_never_reflects_the_request_origin() -> None:
    client = _client()

    response = client.post(
        LOGIN_URL, headers={"Origin": OTHER_ORIGIN}, follow_redirects=False
    )

    assert response.status_code == 403
    assert OTHER_ORIGIN not in str(response.headers)
    assert "access-control-allow-origin" not in response.headers


# --- 9. Business errors collapse into one identical 503 ---------------------


def test_missing_active_configuration_is_a_neutral_503() -> None:
    client = _client(RecordingLookup(None))

    response = _post(client)

    assert response.status_code == 503
    _assert_no_side_effects(response)


def test_a_creation_conflict_is_a_neutral_503() -> None:
    client = _client(store=RecordingStore(added=False))

    response = _post(client)

    assert response.status_code == 503
    _assert_no_side_effects(response)


def test_both_login_failures_are_byte_identical() -> None:
    unavailable = _post(_client(RecordingLookup(None)))
    conflict = _post(_client(store=RecordingStore(added=False)))

    assert unavailable.status_code == conflict.status_code == 503
    assert unavailable.content == conflict.content == b""
    for header in ("cache-control", "content-length"):
        assert unavailable.headers.get(header) == conflict.headers.get(header)
    assert unavailable.headers.get("set-cookie") is None
    assert conflict.headers.get("set-cookie") is None


def test_the_two_error_codes_never_appear_in_the_response() -> None:
    for response in (
        _post(_client(RecordingLookup(None))),
        _post(_client(store=RecordingStore(added=False))),
    ):
        rendered = f"{response.text}{response.headers}"
        assert OidcLoginUnavailable.code not in rendered
        assert OidcLoginStartConflict.code not in rendered


# --- 10. Internal failures collapse into one neutral 500 --------------------


class _SecretBearingError(Exception):
    def __init__(self) -> None:
        super().__init__("issuer https://idp.example.test is unreachable")


@pytest.mark.parametrize(
    "app_arguments",
    [
        {"lookup": RecordingLookup(error=_SecretBearingError())},
        {"store": RecordingStore(error=_SecretBearingError())},
        {"generator": RecordingGenerator(error=_SecretBearingError())},
    ],
)
def test_an_infrastructure_failure_is_a_neutral_500(
    app_arguments: dict[str, Any],
) -> None:
    client = _client(**app_arguments)

    response = _post(client)

    assert response.status_code == 500
    _assert_no_side_effects(response)
    assert "idp.example.test" not in f"{response.text}{response.headers}"


class FailingClock:
    """A clock that raises instead of answering, counting its one call."""

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error or _SecretBearingError()
        self.calls = 0

    def __call__(self) -> datetime:
        self.calls += 1
        raise self._error


def test_a_failing_clock_is_a_neutral_500_without_reaching_the_use_case() -> None:
    lookup = RecordingLookup(_configuration())
    store = RecordingStore()
    generator = RecordingGenerator()
    clock = FailingClock()
    client = _client(lookup, store, generator, clock)

    response = _post(client)

    assert response.status_code == 500
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert response.headers.get("set-cookie") is None
    assert response.headers.get("location") is None
    assert "retry-after" not in response.headers
    assert "idp.example.test" not in f"{response.text}{response.headers}"
    # Read at most once, and nothing downstream ran.
    assert clock.calls == 1
    assert lookup.calls == 0
    assert generator.calls == 0
    assert store.calls == []


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("clock-skew-detected"),
        OSError("no-clock-source-available"),
        ValueError("naive-clock-configured"),
    ],
)
def test_any_clock_failure_collapses_into_the_same_neutral_500(
    error: Exception,
) -> None:
    client = _client(clock=FailingClock(error))

    response = _post(client)

    assert response.status_code == 500
    _assert_no_side_effects(response)
    assert str(error) not in f"{response.text}{response.headers}"


@pytest.mark.parametrize(
    "headers",
    [{}, {"Origin": OTHER_ORIGIN}, {"Origin": ORIGIN, "Sec-Fetch-Site": "cross-site"}],
)
def test_a_failing_clock_is_never_reached_by_a_rejected_request(
    headers: dict[str, str],
) -> None:
    clock = FailingClock()
    client = _client(clock=clock)

    response = client.post(LOGIN_URL, headers=headers, follow_redirects=False)

    assert response.status_code == 403
    assert clock.calls == 0


def test_a_failing_clock_is_never_reached_by_a_non_empty_input() -> None:
    clock = FailingClock()
    client = _client(clock=clock)

    response = _post(client, params={"issuer": ISSUER})

    assert response.status_code == 400
    assert clock.calls == 0


def test_a_naive_clock_fails_neutrally_without_a_cookie() -> None:
    client = _client(clock=RecordingClock(datetime(2026, 8, 4, 12)))

    response = _post(client)

    assert response.status_code == 500
    _assert_no_side_effects(response)


def test_a_builder_failure_after_a_successful_store_is_a_neutral_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _explode(configuration: Any, started: Any) -> OidcAuthorizationRequest:
        raise _SecretBearingError()

    monkeypatch.setattr(
        use_case_module, "build_oidc_authorization_request", _explode
    )
    store = RecordingStore()
    client = _client(store=store)

    response = _post(client)

    assert response.status_code == 500
    _assert_no_side_effects(response)
    # The orphaned pending record stays and is never rolled back.
    assert len(store.calls) == 1


# --- 11. Method boundary ----------------------------------------------------


OTHER_METHODS = [
    "GET",
    "HEAD",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "TRACE",
    "CONNECT",
]


@pytest.mark.parametrize("method", OTHER_METHODS)
def test_any_other_method_is_an_empty_405_allowing_only_post(method: str) -> None:
    lookup = RecordingLookup(_configuration())
    store = RecordingStore()
    generator = RecordingGenerator()
    clock = RecordingClock()
    client = _client(lookup, store, generator, clock)

    response = client.request(
        method, LOGIN_URL, headers=SAME_ORIGIN_HEADERS, follow_redirects=False
    )

    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    assert response.headers["cache-control"] == "no-store"
    _assert_no_side_effects(response, lookup, store, generator, clock)


@pytest.mark.parametrize("method", ["TRACE", "CONNECT"])
def test_trace_and_connect_are_answered_route_locally(method: str) -> None:
    """Not left to a default handler: the body must stay empty like every other."""

    clock = FailingClock()
    client = _client(clock=clock)

    response = client.request(method, LOGIN_URL, follow_redirects=False)

    assert response.status_code == 405
    assert response.content == b""
    assert response.headers["allow"] == "POST"
    assert response.headers["cache-control"] == "no-store"
    assert "detail" not in response.text
    assert clock.calls == 0


def test_every_non_post_method_answers_identically() -> None:
    client = _client()
    answers = {
        method: client.request(method, LOGIN_URL, follow_redirects=False)
        for method in OTHER_METHODS
    }

    for method, response in answers.items():
        assert response.status_code == 405, method
        assert response.headers["allow"] == "POST", method
        assert response.headers["cache-control"] == "no-store", method
        # HEAD legitimately carries no body of its own; the rest must be empty.
        if method != "HEAD":
            assert response.content == b"", method


def test_a_get_with_a_valid_origin_is_still_a_405() -> None:
    clock = RecordingClock()
    client = _client(clock=clock)

    response = client.get(
        LOGIN_URL, headers=SAME_ORIGIN_HEADERS, follow_redirects=False
    )

    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    assert clock.calls == 0


def test_a_405_carries_no_json_detail() -> None:
    client = _client()

    response = client.get(LOGIN_URL, follow_redirects=False)

    assert response.content == b""
    assert "detail" not in response.text


# --- 12. The logout route stays unchanged alongside the new one -------------


def test_logout_route_is_unaffected_by_the_login_start_dependencies() -> None:
    client = _client()

    response = client.post("/v1/session/logout")

    assert response.status_code == 404  # still absent without its own wiring
