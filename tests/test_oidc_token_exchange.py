import inspect
import json
from dataclasses import FrozenInstanceError, fields
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qsl

import httpx2
import pytest

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_token_exchange import (
    OidcIdToken,
    OidcTokenEndpointClient,
)
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy


ISSUER = "https://idp.example.test"
TOKEN_ENDPOINT = f"{ISSUER}/token"
CLIENT_ID = "liquent-control-plane"
CODE = "authorization-code-1"
CODE_VERIFIER = "code-verifier-1"
REDIRECT_URI = "https://app.example.test/v1/session/oidc/callback"
ID_TOKEN = "header.payload.signature"
MAX_BYTES = 4096

JSON_HEADERS = {"content-type": "application/json"}


def _configuration(**overrides: Any) -> TrustedOidcClientConfiguration:
    arguments: dict[str, Any] = {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scopes": ("openid",),
        "token_endpoint": TOKEN_ENDPOINT,
        "jwks_uri": f"{ISSUER}/jwks",
        "allowed_signing_algorithms": ("RS256",),
        "clock_skew": timedelta(seconds=30),
    }
    arguments.update(overrides)
    return TrustedOidcClientConfiguration(**arguments)


def _verification() -> OidcAuthorizationCodeVerification:
    return OidcAuthorizationCodeVerification(
        authorization_code=CODE,
        expected_issuer=ISSUER,
        expected_nonce="expected-nonce-1",
        code_verifier=CODE_VERIFIER,
        redirect_uri=REDIRECT_URI,
    )


def _policy(**overrides: Any) -> OidcVerificationPolicy:
    arguments: dict[str, Any] = {
        "connect_timeout": timedelta(seconds=2),
        "read_timeout": timedelta(seconds=5),
        "total_timeout": timedelta(seconds=10),
        "token_response_max_bytes": MAX_BYTES,
        "jwks_response_max_bytes": MAX_BYTES,
        "jwks_cache_ttl": timedelta(minutes=5),
    }
    arguments.update(overrides)
    return OidcVerificationPolicy(**arguments)


class Recorder:
    """Counts requests and keeps the last one for exact assertions."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []
        self.responses: list[httpx2.Response] = []


def _exchange(
    handler: Any,
    *,
    policy: OidcVerificationPolicy | None = None,
    monotonic: Any = None,
    recorder: Recorder | None = None,
) -> Any:
    recorder = recorder if recorder is not None else Recorder()

    def wrapped(request: httpx2.Request) -> httpx2.Response:
        recorder.requests.append(request)
        response = handler(request)
        recorder.responses.append(response)
        return response

    arguments: dict[str, Any] = {}
    if monotonic is not None:
        arguments["monotonic"] = monotonic
    with httpx2.Client(transport=httpx2.MockTransport(wrapped)) as client:
        exchange = OidcTokenEndpointClient(client, policy or _policy(), **arguments)
        return exchange.exchange_authorization_code(_configuration(), _verification())


def _json_response(
    payload: dict[str, Any], status: int = 200, **headers: str
) -> httpx2.Response:
    body = json.dumps(payload).encode()
    return httpx2.Response(
        status, headers={**JSON_HEADERS, **headers}, content=iter([body])
    )


def _ok(request: httpx2.Request) -> httpx2.Response:
    return _json_response({"id_token": ID_TOKEN, "access_token": "a", "scope": "openid"})


# --- 1. OidcIdToken --------------------------------------------------------

def test_id_token_is_frozen_slotted_hashable_and_repr_free() -> None:
    token = OidcIdToken(ID_TOKEN)

    with pytest.raises(FrozenInstanceError):
        token.value = "other"  # type: ignore[misc]
    assert OidcIdToken.__slots__ == ("value",)
    assert [field.name for field in fields(OidcIdToken)] == ["value"]
    assert hash(token) == hash(OidcIdToken(ID_TOKEN))
    assert token.value == ID_TOKEN
    assert repr(token) == "OidcIdToken()"
    assert ID_TOKEN not in repr(token)


@pytest.mark.parametrize("value", ["", None, 1, b"token"])
def test_an_empty_or_wrong_typed_id_token_is_rejected(value: Any) -> None:
    with pytest.raises(ValueError, match="id token must be a non-empty string"):
        OidcIdToken(value)


# --- 2. The exact request --------------------------------------------------

def test_a_successful_exchange_sends_exactly_one_shaped_post() -> None:
    recorder = Recorder()

    result = _exchange(_ok, recorder=recorder)

    assert len(recorder.requests) == 1
    request = recorder.requests[0]
    assert request.method == "POST"
    assert str(request.url) == TOKEN_ENDPOINT
    assert dict(parse_qsl(request.content.decode())) == {
        "grant_type": "authorization_code",
        "code": CODE,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": CODE_VERIFIER,
    }
    headers = {name.lower(): value for name, value in request.headers.items()}
    assert headers["accept"] == "application/json"
    assert headers["accept-encoding"] == "identity"
    assert "cookie" not in headers
    assert result == OidcIdToken(ID_TOKEN)
    assert repr(result) == "OidcIdToken()"


def test_no_secret_or_extra_field_travels_in_the_form() -> None:
    recorder = Recorder()

    _exchange(_ok, recorder=recorder)

    sent = dict(parse_qsl(recorder.requests[0].content.decode()))
    assert set(sent) == {
        "grant_type", "code", "redirect_uri", "client_id", "code_verifier"
    }
    for forbidden in ("client_secret", "state", "nonce", "issuer", "scope"):
        assert forbidden not in sent


# --- 3. Exactly one request, never retried ---------------------------------

@pytest.mark.parametrize(
    "handler",
    [
        lambda request: (_ for _ in ()).throw(httpx2.ConnectError("boom")),
        lambda request: _json_response({}, status=500),
        lambda request: httpx2.Response(
            200, headers=JSON_HEADERS, content=iter([b"not-json"])
        ),
    ],
)
def test_a_failure_is_never_retried(handler: Any) -> None:
    recorder = Recorder()

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(handler, recorder=recorder)

    assert len(recorder.requests) == 1


# --- 4. Redirects ----------------------------------------------------------

@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_a_redirect_is_not_followed(status: int) -> None:
    recorder = Recorder()

    def redirector(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, headers={"location": "https://evil.test/x"})

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(redirector, recorder=recorder)

    assert len(recorder.requests) == 1  # the redirect target was never fetched


# --- 5. Size limit ---------------------------------------------------------

def _padded(size: int) -> dict[str, Any]:
    """A JSON object whose encoded form is exactly ``size`` bytes."""

    base = {"id_token": ID_TOKEN, "pad": ""}
    return {**base, "pad": "p" * (size - len(json.dumps(base).encode()))}


def test_a_body_exactly_at_the_limit_is_accepted() -> None:
    payload = _padded(MAX_BYTES)
    assert len(json.dumps(payload).encode()) == MAX_BYTES

    assert _exchange(lambda request: _json_response(payload)) == OidcIdToken(ID_TOKEN)


def test_a_body_one_byte_over_the_limit_is_refused() -> None:
    payload = _padded(MAX_BYTES + 1)

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(lambda request: _json_response(payload))


def test_chunks_are_counted_cumulatively() -> None:
    oversized = b"x" * (MAX_BYTES + 1)
    chunks = [oversized[i : i + 512] for i in range(0, len(oversized), 512)]

    def chunked(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, headers=JSON_HEADERS, content=iter(chunks))

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(chunked)


def test_reading_stops_early_instead_of_loading_the_whole_response() -> None:
    """The body must never be fully materialised before the cap is applied."""

    produced = 0
    chunk_size = 512
    offered = (MAX_BYTES // chunk_size) * 20  # far more than the cap allows

    def flood(request: httpx2.Request) -> httpx2.Response:
        def stream() -> Any:
            nonlocal produced
            for _ in range(offered):
                produced += 1
                yield b"x" * chunk_size

        return httpx2.Response(200, headers=JSON_HEADERS, content=stream())

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(flood)

    # Reading stops within one read buffer of the cap instead of draining the
    # peer. The exact count depends on the internal buffer size, so the check
    # is that only a small fraction of what was offered was ever pulled.
    assert produced < offered // 4


@pytest.mark.parametrize("declared", [str(MAX_BYTES + 1), "not-a-number", "-1"])
def test_an_unusable_or_oversized_content_length_is_refused(declared: str) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        response = _json_response({"id_token": ID_TOKEN})
        response.headers["content-length"] = declared
        return response

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(handler)


# --- 6. Content type and encoding ------------------------------------------

@pytest.mark.parametrize(
    "content_type",
    ["application/json", "application/json; charset=utf-8", "APPLICATION/JSON"],
)
def test_an_accepted_media_type_succeeds(content_type: str) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"content-type": content_type},
            content=iter([json.dumps({"id_token": ID_TOKEN}).encode()]),
        )

    assert _exchange(handler) == OidcIdToken(ID_TOKEN)


@pytest.mark.parametrize(
    "headers",
    [
        {"content-type": "text/html"},
        {"content-type": "application/jwt"},
        {},  # no content type at all
        {"content-type": "application/json", "content-encoding": "gzip"},
    ],
)
def test_a_wrong_media_type_or_compression_is_refused(headers: dict[str, str]) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, headers=headers, content=iter([json.dumps({"id_token": ID_TOKEN}).encode()])
        )

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(handler)


# --- 7. JSON and status boundary -------------------------------------------

def test_a_valid_oauth_error_response_rejects_the_code() -> None:
    for status in (400, 401):
        result = _exchange(
            lambda request, status=status: _json_response(
                {"error": "invalid_grant", "error_description": "code already used"},
                status=status,
            )
        )
        assert result is None


@pytest.mark.parametrize(
    ("status", "payload"),
    [
        (200, {}),  # no id_token
        (200, {"id_token": ""}),
        (200, {"id_token": 1}),
        (200, {"id_token": ID_TOKEN, "error": "invalid_grant"}),  # mixed
        (400, {}),  # malformed error object
        (400, {"error": ""}),
        (400, {"error": 1}),
        (400, {"error": "invalid_grant", "id_token": ID_TOKEN}),
        (403, {"error": "invalid_grant"}),  # unexpected status
        (500, {"error": "server_error"}),
        (204, {}),
    ],
)
def test_an_unusable_status_or_payload_is_unavailable(
    status: int, payload: dict[str, Any]
) -> None:
    with pytest.raises(OidcVerificationUnavailable):
        _exchange(lambda request: _json_response(payload, status=status))


@pytest.mark.parametrize("body", [b"", b"null", b"[]", b'"text"', b"\xff\xfe"])
def test_a_non_object_or_undecodable_body_is_unavailable(body: bytes) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, headers=JSON_HEADERS, content=iter([body]))

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(handler)


def test_extra_token_fields_are_ignored_and_not_stored() -> None:
    result = _exchange(
        lambda request: _json_response(
            {
                "id_token": ID_TOKEN,
                "access_token": "access-secret",
                "refresh_token": "refresh-secret",
                "token_type": "Bearer",
            }
        )
    )

    assert result == OidcIdToken(ID_TOKEN)
    assert [field.name for field in fields(OidcIdToken)] == ["value"]
    assert "access-secret" not in repr(result)


# --- 8. Time ---------------------------------------------------------------

@pytest.mark.parametrize(
    "error", [httpx2.ConnectTimeout("c"), httpx2.ReadTimeout("r"), httpx2.PoolTimeout("p")]
)
def test_a_transport_timeout_is_unavailable(error: Exception) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise error

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(handler)


def test_the_client_receives_the_configured_phase_timeouts() -> None:
    seen: dict[str, Any] = {}

    class RecordingClient(httpx2.Client):
        def stream(self, *args: Any, **kwargs: Any) -> Any:
            seen["timeout"] = kwargs.get("timeout")
            seen["follow_redirects"] = kwargs.get("follow_redirects")
            return super().stream(*args, **kwargs)

    with RecordingClient(transport=httpx2.MockTransport(_ok)) as client:
        OidcTokenEndpointClient(client, _policy()).exchange_authorization_code(
            _configuration(), _verification()
        )

    assert seen["follow_redirects"] is False
    assert seen["timeout"] == httpx2.Timeout(connect=2.0, read=5.0, write=10.0, pool=10.0)


@pytest.mark.parametrize("readings", [[0.0, 10.0], [0.0, 0.0, 10.0], [0.0, 0.0, 0.0, 10.0]])
def test_exceeding_the_total_time_between_steps_is_unavailable(
    readings: list[float],
) -> None:
    """The bound is checked after headers, after each chunk, and before return."""

    values = iter(readings + [10.0] * 8)

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(_ok, monotonic=lambda: next(values))


@pytest.mark.parametrize("reading", [float("nan"), float("inf"), True])
def test_a_technically_unusable_clock_is_unavailable(reading: Any) -> None:
    with pytest.raises(OidcVerificationUnavailable) as raised:
        _exchange(_ok, monotonic=lambda: reading)

    assert str(raised.value) == "oidc_verification_unavailable"


# --- 9. The response is always closed --------------------------------------

@pytest.mark.parametrize("succeeds", [True, False])
def test_the_response_is_closed_on_every_path(succeeds: bool) -> None:
    recorder = Recorder()
    handler = _ok if succeeds else (lambda request: _json_response({}, status=500))

    try:
        _exchange(handler, recorder=recorder)
    except OidcVerificationUnavailable:
        pass

    assert recorder.responses and all(r.is_closed for r in recorder.responses)


# --- 10. Signatures --------------------------------------------------------

def test_public_signatures_are_exactly_as_agreed() -> None:
    init = inspect.signature(OidcTokenEndpointClient.__init__)
    assert list(init.parameters) == ["self", "client", "policy", "monotonic"]

    exchange = inspect.signature(
        OidcTokenEndpointClient.exchange_authorization_code
    )
    assert list(exchange.parameters) == ["self", "configuration", "verification"]

    public = [
        name
        for name in vars(OidcTokenEndpointClient)
        if not name.startswith("_")
    ]
    assert public == ["exchange_authorization_code"]
