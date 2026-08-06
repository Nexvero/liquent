import json
from dataclasses import FrozenInstanceError
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
UNAVAILABLE = "unavailable"

POLICY = OidcVerificationPolicy(
    connect_timeout=timedelta(seconds=2),
    read_timeout=timedelta(seconds=5),
    total_timeout=timedelta(seconds=10),
    token_response_max_bytes=MAX_BYTES,
    jwks_response_max_bytes=MAX_BYTES,
    jwks_cache_ttl=timedelta(minutes=5),
)
CONFIGURATION = TrustedOidcClientConfiguration(
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
VERIFICATION = OidcAuthorizationCodeVerification(
    authorization_code=CODE,
    expected_issuer=ISSUER,
    expected_nonce="expected-nonce-1",
    code_verifier=CODE_VERIFIER,
    redirect_uri=REDIRECT_URI,
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
            client, POLICY, **arguments
        ).exchange_authorization_code(CONFIGURATION, VERIFICATION)


def _responds(body: Any, status: int = 200, **headers: str) -> Any:
    """A handler returning ``body`` as raw bytes or as encoded JSON."""

    content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return lambda request: httpx2.Response(
        status, headers={**JSON_HEADERS, **headers}, content=iter([content])
    )


def _connect_error(request: httpx2.Request) -> httpx2.Response:
    raise httpx2.ConnectError("boom")


def _clock(*readings: Any, raises_at: int = 0) -> Any:
    """Build a fresh clock per test, returning each reading then the last.

    With ``raises_at`` that read and every later one raise instead.
    """

    def build() -> Any:
        remaining, reads = list(readings), [0]

        def clock() -> float:
            reads[0] += 1
            if raises_at and reads[0] >= raises_at:
                raise RuntimeError("CLOCK-INTERNAL-DETAIL")
            return remaining.pop(0) if len(remaining) > 1 else remaining[0]

        return clock

    return build


def _assert_neutral(raised: Any) -> None:
    assert raised.value.args == ("oidc_verification_unavailable",)


_OK = _responds({"id_token": ID_TOKEN, "access_token": "a", "scope": "openid"})


def test_a_successful_exchange_sends_exactly_one_shaped_post() -> None:
    seen: list[Any] = []

    result = _exchange(_OK, seen=seen)

    assert len(seen) == 1
    request, response = seen[0]
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
    # The policy bounds every phase, and nothing is taken from the response.
    assert request.extensions["timeout"] == {
        "connect": 2.0,
        "read": 5.0,
        "write": 10.0,
        "pool": 10.0,
    }
    assert response.is_closed
    # Access token and scope are ignored, and the value never reaches repr.
    assert result == OidcIdToken(ID_TOKEN)
    assert repr(result) == "OidcIdToken()"


@pytest.mark.parametrize(
    "handler",
    [
        _connect_error,
        _responds({}, status=500),
        lambda request: httpx2.Response(302, headers={"location": "https://evil.test"}),
    ],
    ids=["transport-fault", "server-error", "redirect"],
)
def test_a_failure_is_never_retried_and_the_stream_is_always_closed(
    handler: Any,
) -> None:
    seen: list[Any] = []

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(handler, seen=seen)

    assert len(seen) <= 1
    assert all(response.is_closed for _, response in seen)


def test_the_body_is_bounded_incrementally() -> None:
    """The cap counts read bytes and applies before the body is materialised."""

    def padded(size: int) -> bytes:
        base = {"id_token": ID_TOKEN, "pad": ""}
        filler = "p" * (size - len(json.dumps(base).encode()))
        return json.dumps({**base, "pad": filler}).encode()

    assert len(padded(MAX_BYTES)) == MAX_BYTES
    assert _exchange(_responds(padded(MAX_BYTES))) == OidcIdToken(ID_TOKEN)
    with pytest.raises(OidcVerificationUnavailable):
        _exchange(_responds(padded(MAX_BYTES + 1)))

    produced, offered = 0, 500

    def flood(request: httpx2.Request) -> httpx2.Response:
        def stream() -> Any:
            nonlocal produced
            for _ in range(offered):
                produced += 1
                yield b"x" * 512

        return httpx2.Response(200, headers=JSON_HEADERS, content=stream())

    with pytest.raises(OidcVerificationUnavailable):
        _exchange(flood)
    # Only a fraction is ever pulled from the peer.
    assert produced < offered // 4


def _length(value: str) -> dict[str, str]:
    return {**JSON_HEADERS, "content-length": value}


@pytest.mark.parametrize(
    ("headers", "usable"),
    [
        # Media type and charset: case-insensitive, quoted, UTF-8 only.
        ({"content-type": "APPLICATION/JSON"}, True),
        ({"content-type": 'application/json; charset="UTF-8"'}, True),
        ({"content-type": "application/json; charset=iso-8859-1"}, False),
        ({"content-type": "application/json; charset="}, False),
        ({"content-type": "text/html"}, False),
        ({}, False),  # no content type at all
        ({**JSON_HEADERS, "content-encoding": "gzip"}, False),
        # Content-Length: only ASCII digits after permitted HTTP whitespace.
        (_length(" 40 "), True),
        (_length("+40"), False),
        (_length("-1"), False),
        (_length("40.0"), False),
        (_length("40, 40"), False),
        (_length(""), False),
        (_length(str(MAX_BYTES + 1)), False),  # refused before any body is read
    ],
)
def test_only_strictly_framed_uncompressed_json_is_accepted(
    headers: dict[str, str], usable: bool
) -> None:
    body = json.dumps({"id_token": ID_TOKEN}).encode()
    assert len(body) == 40

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, headers=headers, content=iter([body]))

    if usable:
        assert _exchange(handler) == OidcIdToken(ID_TOKEN)
    else:
        with pytest.raises(OidcVerificationUnavailable):
            _exchange(handler)


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (200, b'{"id_token":"header.payload.signature","access_token":"a"}', ID_TOKEN),
        (400, b'{"error":"invalid_grant","error_description":"used"}', None),
        (401, b'{"error":"invalid_grant"}', None),
        # Mixed answers are refused on key presence, whatever the value.
        (200, b'{"id_token":"t","error":null}', UNAVAILABLE),
        (400, b'{"error":"invalid_grant","id_token":null}', UNAVAILABLE),
        # Incomplete answers in either direction.
        (200, b"{}", UNAVAILABLE),
        (200, b'{"id_token":""}', UNAVAILABLE),
        (400, b"{}", UNAVAILABLE),
        (400, b'{"error":""}', UNAVAILABLE),
        # A repeated member must not be resolved by last-value-wins.
        (200, b'{"id_token":"first","id_token":"second"}', UNAVAILABLE),
        (400, b'{"error":"a","error":"b"}', UNAVAILABLE),
        # Unparsable, non-object, and unusable statuses.
        (200, b"", UNAVAILABLE),
        (200, b"[]", UNAVAILABLE),
        # Decoding is strict: a lenient one would hand on a corrupted token.
        (200, b'{"id_token":"a\xffb"}', UNAVAILABLE),
        (403, b'{"error":"invalid_grant"}', UNAVAILABLE),
    ],
)
def test_the_status_and_payload_decide_the_classification(
    status: int, body: bytes, expected: str | None
) -> None:
    if expected == UNAVAILABLE:
        with pytest.raises(OidcVerificationUnavailable) as raised:
            _exchange(_responds(body, status=status))
        _assert_neutral(raised)
    else:
        result = _exchange(_responds(body, status=status))
        assert result == (OidcIdToken(expected) if expected else None)


@pytest.mark.parametrize(
    "build_clock",
    [
        _clock(0.0, 10.0),  # deadline reached after the headers
        _clock(0.0, 0.0, 10.0),  # reached after a chunk
        _clock(0.0, 0.0, 0.0, 10.0),  # reached before returning
        _clock(100.0, 50.0),  # running backwards is unusable, not fast
        _clock(float("nan")),  # not finite
        _clock(True),  # bool is an int subclass but never a reading
        _clock("0"),  # not a number at all
        _clock(0.0, raises_at=1),  # the first read raises
        _clock(0.0, raises_at=2),  # a read during response processing raises
    ],
    ids="after-headers after-chunk before-return backwards not-finite bool "
    "not-a-number raises-first raises-later".split(),
)
def test_an_unusable_clock_or_exceeded_deadline_is_neutral(build_clock: Any) -> None:
    with pytest.raises(OidcVerificationUnavailable) as raised:
        _exchange(_OK, monotonic=build_clock())

    _assert_neutral(raised)
    assert "CLOCK-INTERNAL-DETAIL" not in f"{raised.value!r}{raised.value.args}"


@pytest.mark.parametrize(
    "handler",
    [
        _responds({"error": "invalid_grant", "error_description": "LEAK"}, status=400),
        _responds({"id_token": ID_TOKEN, "error": "LEAK"}),
    ],
    ids=["oauth-error", "mixed-answer"],
)
def test_no_secret_or_provider_text_reaches_a_result_or_error(handler: Any) -> None:
    try:
        rendered = repr(_exchange(handler))
    except OidcVerificationUnavailable as error:
        rendered = f"{error!r}{error.args}"

    for secret in (CODE, CODE_VERIFIER, ID_TOKEN, "LEAK", "invalid_grant"):
        assert secret not in rendered


def test_id_token_is_frozen_and_repr_free() -> None:
    token = OidcIdToken(ID_TOKEN)

    with pytest.raises(FrozenInstanceError):
        token.value = "other"  # type: ignore[misc]
    assert token.value == ID_TOKEN
    assert repr(token) == "OidcIdToken()"
    assert hash(token) == hash(OidcIdToken(ID_TOKEN))
    with pytest.raises(ValueError, match="id token must be a non-empty string"):
        OidcIdToken("")
