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


def _configuration() -> TrustedOidcClientConfiguration:
    return TrustedOidcClientConfiguration(
        issuer=ISSUER,
        authorization_endpoint=f"{ISSUER}/authorize",
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scopes=("openid",),
        token_endpoint=TOKEN_ENDPOINT,
        jwks_uri=f"{ISSUER}/jwks",
        allowed_signing_algorithms=("RS256",),
        clock_skew=timedelta(seconds=30),
    )


def _verification() -> OidcAuthorizationCodeVerification:
    return OidcAuthorizationCodeVerification(
        authorization_code=CODE,
        expected_issuer=ISSUER,
        expected_nonce="expected-nonce-1",
        code_verifier=CODE_VERIFIER,
        redirect_uri=REDIRECT_URI,
    )


def _policy() -> OidcVerificationPolicy:
    return OidcVerificationPolicy(
        connect_timeout=timedelta(seconds=2),
        read_timeout=timedelta(seconds=5),
        total_timeout=timedelta(seconds=10),
        token_response_max_bytes=MAX_BYTES,
        jwks_response_max_bytes=MAX_BYTES,
        jwks_cache_ttl=timedelta(minutes=5),
    )


def _exchange(
    handler: Any, *, monotonic: Any = None, seen: list[Any] | None = None
) -> Any:
    """Run one exchange against a mock transport, recording the exchanges."""

    def wrapped(request: httpx2.Request) -> httpx2.Response:
        response = handler(request)
        if seen is not None:
            seen.append((request, response))
        return response

    arguments = {"monotonic": monotonic} if monotonic is not None else {}
    with httpx2.Client(transport=httpx2.MockTransport(wrapped)) as client:
        return OidcTokenEndpointClient(
            client, _policy(), **arguments
        ).exchange_authorization_code(_configuration(), _verification())


def _responds(body: Any, status: int = 200, **headers: str) -> Any:
    """A handler returning ``body`` as raw bytes or as encoded JSON."""

    content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return lambda request: httpx2.Response(
        status, headers={**JSON_HEADERS, **headers}, content=iter([content])
    )


def _raises(error: Exception) -> Any:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise error

    return handler


_OK = _responds({"id_token": ID_TOKEN, "access_token": "a", "scope": "openid"})


# --- Result object ---------------------------------------------------------

def test_id_token_is_frozen_slotted_hashable_and_repr_free() -> None:
    token = OidcIdToken(ID_TOKEN)

    with pytest.raises(FrozenInstanceError):
        token.value = "other"  # type: ignore[misc]
    assert OidcIdToken.__slots__ == ("value",)
    assert [field.name for field in fields(OidcIdToken)] == ["value"]
    assert hash(token) == hash(OidcIdToken(ID_TOKEN))
    assert token.value == ID_TOKEN
    assert repr(token) == "OidcIdToken()"


@pytest.mark.parametrize("value", ["", None])
def test_an_empty_or_wrong_typed_id_token_is_rejected(value: Any) -> None:
    with pytest.raises(ValueError, match="id token must be a non-empty string"):
        OidcIdToken(value)


# --- The exact request -----------------------------------------------------

def test_a_successful_exchange_sends_exactly_one_shaped_post() -> None:
    seen: list[Any] = []

    result = _exchange(_OK, seen=seen)

    assert len(seen) == 1
    request = seen[0][0]
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
    # Extra token fields are ignored and never stored.
    assert result == OidcIdToken(ID_TOKEN)
    assert repr(result) == "OidcIdToken()"


def test_the_request_carries_the_policy_timeouts_and_forbids_redirects() -> None:
    used: dict[str, Any] = {}

    class RecordingClient(httpx2.Client):
        def stream(self, *args: Any, **kwargs: Any) -> Any:
            used.update(kwargs)
            return super().stream(*args, **kwargs)

    with RecordingClient(transport=httpx2.MockTransport(_OK)) as client:
        OidcTokenEndpointClient(client, _policy()).exchange_authorization_code(
            _configuration(), _verification()
        )

    assert used["follow_redirects"] is False
    assert used["timeout"] == httpx2.Timeout(
        connect=2.0, read=5.0, write=10.0, pool=10.0
    )


@pytest.mark.parametrize(
    "handler",
    [
        _raises(httpx2.ConnectError("boom")),
        _raises(httpx2.ConnectTimeout("connect")),
        _raises(httpx2.ReadTimeout("read")),
        _responds({}, status=500),
        lambda request: httpx2.Response(302, headers={"location": "https://evil.test"}),
    ],
)
def test_a_failure_is_never_retried_and_a_redirect_is_never_followed(
    handler: Any,
) -> None:
    seen: list[Any] = []

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(handler, seen=seen)

    assert len(seen) <= 1


# --- Byte limit ------------------------------------------------------------

def _padded(size: int) -> dict[str, Any]:
    base = {"id_token": ID_TOKEN, "pad": ""}
    return {**base, "pad": "p" * (size - len(json.dumps(base).encode()))}


def test_a_body_at_the_limit_is_accepted_and_one_byte_over_is_not() -> None:
    assert len(json.dumps(_padded(MAX_BYTES)).encode()) == MAX_BYTES

    assert _exchange(_responds(_padded(MAX_BYTES))) == OidcIdToken(ID_TOKEN)
    with pytest.raises(OidcVerificationUnavailable):
        _exchange(_responds(_padded(MAX_BYTES + 1)))


def test_reading_stops_early_instead_of_loading_the_whole_response() -> None:
    """The body must never be fully materialised before the cap is applied."""

    produced = 0
    offered = 500

    def flood(request: httpx2.Request) -> httpx2.Response:
        def stream() -> Any:
            nonlocal produced
            for _ in range(offered):
                produced += 1
                yield b"x" * 512

        return httpx2.Response(200, headers=JSON_HEADERS, content=stream())

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(flood)

    # Chunks are counted cumulatively and only a fraction is ever pulled.
    assert produced < offered // 4


@pytest.mark.parametrize(
    ("declared", "usable"),
    [
        ("40", True),
        (" 40 ", True),  # permitted HTTP whitespace
        ("+40", False),
        ("-1", False),
        ("40.0", False),
        ("40, 40", False),
        ("", False),
        ("１０", False),  # non-ASCII digits
        (str(MAX_BYTES + 1), False),  # refused before any body is read
    ],
)
def test_content_length_is_parsed_strictly(declared: str, usable: bool) -> None:
    body = json.dumps({"id_token": ID_TOKEN}).encode()
    assert len(body) == 40
    handler = _responds(body, **{"content-length": declared})

    if usable:
        assert _exchange(handler) == OidcIdToken(ID_TOKEN)
    else:
        with pytest.raises(OidcVerificationUnavailable):
            _exchange(handler)


# --- Media type, charset, encoding -----------------------------------------

@pytest.mark.parametrize(
    ("content_type", "usable"),
    [
        ("application/json", True),
        ("APPLICATION/JSON", True),
        ("application/json; charset=UTF-8", True),
        ('application/json;charset="utf-8"', True),
        ("text/html", False),
        ("application/json; charset=iso-8859-1", False),
        ("application/json; charset=", False),
        (None, False),
    ],
)
def test_only_json_encoded_as_utf_8_is_accepted(
    content_type: str | None, usable: bool
) -> None:
    headers = {} if content_type is None else {"content-type": content_type}

    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.dumps({"id_token": ID_TOKEN}).encode()
        return httpx2.Response(200, headers=headers, content=iter([body]))

    if usable:
        assert _exchange(handler) == OidcIdToken(ID_TOKEN)
    else:
        with pytest.raises(OidcVerificationUnavailable):
            _exchange(handler)


def test_a_compressed_response_is_refused() -> None:
    """Decompression could otherwise expand a small transfer past the cap."""

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(_responds({"id_token": ID_TOKEN}, **{"content-encoding": "gzip"}))


# --- Status and JSON classification ----------------------------------------

@pytest.mark.parametrize("status", [400, 401])
def test_a_valid_oauth_error_response_rejects_the_code(status: int) -> None:
    assert _exchange(
        _responds(
            {"error": "invalid_grant", "error_description": "code already used"},
            status=status,
        )
    ) is None


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, b"{}"),
        (200, b'{"id_token":""}'),
        (200, b'{"id_token":1}'),
        # Mixed answers are classified by key presence, whatever the value.
        (200, b'{"id_token":"t","error":null}'),
        (200, b'{"id_token":"t","error":"invalid_grant"}'),
        (400, b"{}"),
        (400, b'{"error":""}'),
        (400, b'{"error":"invalid_grant","id_token":null}'),
        (400, b'{"error":"invalid_grant","id_token":"t"}'),
        # A repeated member must not be resolved by last-value-wins.
        (200, b'{"id_token":"first","id_token":"second"}'),
        (400, b'{"error":"a","error":"b"}'),
        (200, b'{"id_token":"t","meta":{"k":1,"k":2}}'),
        # Unparsable, non-object, or non-UTF-8 bodies.
        (200, b""),
        (200, b"null"),
        (200, b"[]"),
        (200, b"\xff\xfe"),
        (403, b'{"error":"invalid_grant"}'),
    ],
)
def test_an_unusable_status_or_payload_is_unavailable(status: int, body: bytes) -> None:
    with pytest.raises(OidcVerificationUnavailable):
        _exchange(_responds(body, status=status))


# --- Time ------------------------------------------------------------------

@pytest.mark.parametrize(
    "readings",
    [
        [0.0, 10.0],  # after the headers
        [0.0, 0.0, 10.0],  # after a chunk
        [0.0, 0.0, 0.0, 10.0],  # before returning
        [100.0, 50.0],  # a clock running backwards is unusable, not fast
    ],
)
def test_an_exceeded_or_backwards_total_time_is_unavailable(
    readings: list[float],
) -> None:
    values = iter(readings + [readings[-1]] * 8)

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(_OK, monotonic=lambda: next(values))


@pytest.mark.parametrize("reading", [float("nan"), float("inf"), True, "0"])
def test_a_technically_unusable_clock_reading_is_unavailable(reading: Any) -> None:
    with pytest.raises(OidcVerificationUnavailable) as raised:
        _exchange(_OK, monotonic=lambda: reading)

    assert str(raised.value) == "oidc_verification_unavailable"


@pytest.mark.parametrize("failing_call", [1, 2])
def test_a_raising_clock_is_neutralised_without_leaking_its_error(
    failing_call: int,
) -> None:
    """Covers both the first read and a read during response processing."""

    calls = 0

    def clock() -> float:
        nonlocal calls
        calls += 1
        if calls >= failing_call:
            raise RuntimeError("CLOCK-INTERNAL-DETAIL")
        return 0.0

    with pytest.raises(OidcVerificationUnavailable) as raised:
        _exchange(_OK, monotonic=clock)

    assert "CLOCK-INTERNAL-DETAIL" not in f"{raised.value}{raised.value.args}"


# --- Secret boundary and cleanup -------------------------------------------

@pytest.mark.parametrize(
    "handler",
    [
        _responds({"error": "invalid_grant", "error_description": "LEAK"}, status=400),
        _responds({"id_token": ID_TOKEN, "error": "LEAK"}),
        _responds(b"LEAK-not-json"),
    ],
)
def test_no_secret_or_provider_text_reaches_a_result_or_error(handler: Any) -> None:
    try:
        rendered = repr(_exchange(handler))
    except OidcVerificationUnavailable as error:
        rendered = f"{error}{error.args}"

    for secret in (CODE, CODE_VERIFIER, ID_TOKEN, "LEAK", "invalid_grant"):
        assert secret not in rendered


@pytest.mark.parametrize("handler", [_OK, _responds({}, status=500)])
def test_the_response_is_closed_on_every_path(handler: Any) -> None:
    seen: list[Any] = []

    try:
        _exchange(handler, seen=seen)
    except OidcVerificationUnavailable:
        pass

    assert seen and all(response.is_closed for _, response in seen)


# --- Public surface --------------------------------------------------------

def test_public_signatures_are_exactly_as_agreed() -> None:
    assert list(inspect.signature(OidcTokenEndpointClient.__init__).parameters) == [
        "self",
        "client",
        "policy",
        "monotonic",
    ]
    assert list(
        inspect.signature(
            OidcTokenEndpointClient.exchange_authorization_code
        ).parameters
    ) == ["self", "configuration", "verification"]
    assert [
        name for name in vars(OidcTokenEndpointClient) if not name.startswith("_")
    ] == ["exchange_authorization_code"]
