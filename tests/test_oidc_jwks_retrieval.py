import json
from datetime import timedelta
from typing import Any

import httpx2
import pytest

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_jwks_retrieval import OidcJwksEndpointClient
from liquent_platform.identity.oidc_verification import OidcVerificationUnavailable
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy


ISSUER = "https://idp.example.test"
JWKS_URI = f"{ISSUER}/jwks"
MAX_BYTES = 4096
JSON_HEADERS = {"content-type": "application/json"}

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
    client_id="liquent-control-plane",
    redirect_uri="https://app.example.test/v1/session/oidc/callback",
    scopes=("openid",),
    token_endpoint=f"{ISSUER}/token",
    jwks_uri=JWKS_URI,
    allowed_signing_algorithms=("RS256",),
    clock_skew=timedelta(seconds=30),
)
KEY_SET = {
    "keys": [{"kty": "RSA", "kid": "a", "n": "AQAB", "e": "AQAB", "extra": 1}],
    "unknown_top_level": "kept",
}


def _load(
    handler: Any,
    *,
    monotonic: Any = None,
    seen: list[Any] | None = None,
    policy: OidcVerificationPolicy = POLICY,
    **client_arguments: Any,
) -> Any:
    """Run one retrieval against a mock transport, recording the exchange."""

    def wrapped(request: httpx2.Request) -> httpx2.Response:
        response = handler(request)
        if seen is not None:
            seen.append((request, response))
        return response

    arguments = {"monotonic": monotonic} if monotonic is not None else {}
    with httpx2.Client(
        transport=httpx2.MockTransport(wrapped), **client_arguments
    ) as client:
        return OidcJwksEndpointClient(client, policy, **arguments).load_jwks(
            CONFIGURATION
        )


def _responds(body: Any, status: int = 200, **headers: str) -> Any:
    """A handler returning ``body`` as raw bytes or as encoded JSON."""

    content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return lambda request: httpx2.Response(
        status, headers={**JSON_HEADERS, **headers}, content=iter([content])
    )


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


_OK = _responds(KEY_SET)


def test_one_shaped_get_carries_no_client_credentials() -> None:
    """A preconfigured client must lend this request nothing."""

    seen: list[Any] = []
    cookies = httpx2.Cookies()
    cookies.set("session", "IDP-SESSION-COOKIE", domain="idp.example.test")

    result = _load(
        _OK,
        seen=seen,
        cookies=cookies,
        auth=("operator", "PASSWORD"),
        headers={"x-harmless": "control-value"},
    )

    assert len(seen) == 1
    request, response = seen[0]
    assert request.method == "GET"
    assert str(request.url) == JWKS_URI
    assert request.content == b""
    headers = {name.lower(): value for name, value in request.headers.items()}
    assert headers["accept"] == "application/json"
    assert headers["accept-encoding"] == "identity"
    assert "cookie" not in headers
    assert "authorization" not in headers
    # The control header proves nothing is stripped wholesale.
    assert headers["x-harmless"] == "control-value"
    # The policy bounds every phase; nothing is taken from the response.
    assert request.extensions["timeout"] == {
        "connect": 2.0,
        "read": 5.0,
        "write": 10.0,
        "pool": 10.0,
    }
    assert response.is_closed
    # Passed on as parsed: order, unknown fields, and entry contents survive.
    assert result == KEY_SET
    assert list(result) == ["keys", "unknown_top_level"]
    assert list(result["keys"][0]) == ["kty", "kid", "n", "e", "extra"]


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: (_ for _ in ()).throw(httpx2.ConnectError("boom")),
        lambda request: httpx2.Response(302, headers={"location": "https://evil.test"}),
        _responds(KEY_SET, status=500),
    ],
    ids=["transport-fault", "redirect", "server-error"],
)
def test_a_failure_is_never_retried_and_no_redirect_is_followed(handler: Any) -> None:
    seen: list[Any] = []

    with pytest.raises(OidcVerificationUnavailable):
        _load(handler, seen=seen)

    assert len(seen) <= 1
    assert all(response.is_closed for _, response in seen)


@pytest.mark.parametrize(
    "build_clock",
    [
        _clock(0.0, 10.0),  # deadline reached after the headers
        _clock(0.0, 0.0, 10.0),  # reached while streaming
        _clock(0.0, 5.0, 4.0),  # steps back between two later reads
        _clock(float("nan")),  # not finite
        _clock(True),  # bool is an int subclass but never a reading
        _clock("0"),  # not a number at all
        _clock(0.0, raises_at=1),  # the clock itself raises
    ],
    ids=[
        "deadline-after-headers",
        "deadline-while-streaming",
        "steps-back-later",
        "not-finite",
        "bool",
        "not-a-number",
        "raises",
    ],
)
def test_an_unusable_clock_or_exceeded_deadline_is_neutral(build_clock: Any) -> None:
    with pytest.raises(OidcVerificationUnavailable) as raised:
        _load(_OK, monotonic=build_clock())

    assert raised.value.args == ("oidc_verification_unavailable",)
    assert "CLOCK-INTERNAL-DETAIL" not in f"{raised.value!r}{raised.value.args}"


def test_a_base_exception_from_the_clock_propagates_unchanged() -> None:
    """Cancellation must never be swallowed into a neutral unavailability."""

    class Cancelled(BaseException):
        pass

    def clock() -> float:
        raise Cancelled("propagated")

    with pytest.raises(Cancelled, match="propagated"):
        _load(_OK, monotonic=clock)


def test_the_body_is_bounded_by_declared_and_by_actual_size() -> None:
    assert _load(_responds(KEY_SET, **{"content-length": "105"})) == KEY_SET

    # Declared above the cap: refused before any body is read.
    with pytest.raises(OidcVerificationUnavailable):
        _load(_responds(KEY_SET, **{"content-length": str(MAX_BYTES + 1)}))

    # Under-declared: the cumulative count of read bytes still stops it, and
    # the body is never fully materialised first.
    produced, offered = 0, 500

    def flood(request: httpx2.Request) -> httpx2.Response:
        def stream() -> Any:
            nonlocal produced
            for _ in range(offered):
                produced += 1
                yield b"x" * 512

        return httpx2.Response(200, headers=JSON_HEADERS, content=stream())

    with pytest.raises(OidcVerificationUnavailable):
        _load(flood)
    assert produced < offered // 4


@pytest.mark.parametrize(
    ("headers", "usable"),
    [
        ({"content-type": "APPLICATION/JSON"}, True),
        ({"content-type": "application/json; charset=UTF-8"}, True),
        ({"content-type": 'application/json; charset="utf-8"'}, True),
        # One optional quote pair only; nothing is normalized away.
        ({"content-type": 'application/json; charset="utf-8'}, False),
        ({"content-type": 'application/json; charset=utf-8"'}, False),
        ({"content-type": 'application/json; charset=""utf-8""'}, False),
        ({"content-type": "application/json; charset=utf-8; charset=iso-8859-1"}, False),
        ({"content-type": "text/html"}, False),
        ({**JSON_HEADERS, "content-encoding": "gzip"}, False),
        # One representative Content-Length parser branch: not ASCII digits.
        ({**JSON_HEADERS, "content-length": "+105"}, False),
    ],
)
def test_only_uncompressed_json_encoded_as_utf_8_is_accepted(
    headers: dict[str, str], usable: bool
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200, headers=headers, content=iter([json.dumps(KEY_SET).encode()])
        )

    if usable:
        assert _load(handler) == KEY_SET
    else:
        with pytest.raises(OidcVerificationUnavailable):
            _load(handler)


@pytest.mark.parametrize(
    "body",
    [
        b'{"keys":[{"kid":"a\xffb"}]}',  # strict UTF-8, no lenient fallback
        b'{"keys":[',  # unparsable JSON
        b"[]",  # top level is not an object
        b'{"keys":{"kid":"a"}}',  # keys absent or not an array
        b'{"keys":["not-an-object"]}',  # an entry is not an object
        b'{"keys":[],"keys":[]}',  # duplicate member at the top level
        b'{"keys":[{"kid":"a","kid":"b"}]}',  # duplicate inside a key object
    ],
    ids=[
        "invalid-utf-8",
        "unparsable-json",
        "top-level-not-an-object",
        "keys-not-an-array",
        "entry-not-an-object",
        "duplicate-top-level-member",
        "duplicate-member-in-a-key",
    ],
)
def test_an_unusable_json_or_key_set_shape_is_neutral(body: bytes) -> None:
    with pytest.raises(OidcVerificationUnavailable) as raised:
        _load(_responds(body))

    assert raised.value.args == ("oidc_verification_unavailable",)


def test_a_parser_fault_from_deep_nesting_is_neutral() -> None:
    """RecursionError derives from RuntimeError, not ValueError."""

    generous = OidcVerificationPolicy(
        connect_timeout=timedelta(seconds=2),
        read_timeout=timedelta(seconds=5),
        total_timeout=timedelta(seconds=10),
        token_response_max_bytes=MAX_BYTES,
        jwks_response_max_bytes=131072,
        jwks_cache_ttl=timedelta(minutes=5),
    )
    depth = 20000
    body = b"[" * depth + b"]" * depth
    assert len(body) < generous.jwks_response_max_bytes

    with pytest.raises(OidcVerificationUnavailable) as raised:
        _load(_responds(body), policy=generous)

    assert raised.value.args == ("oidc_verification_unavailable",)


def test_no_url_body_header_or_key_material_reaches_an_error() -> None:
    handler = _responds(
        {"keys": [{"kty": "RSA", "n": "SECRET-MODULUS"}], "error": "PROVIDER-TEXT"},
        status=503,
        **{"content-type": "text/html; charset=LEAKY-CHARSET"},
    )

    with pytest.raises(OidcVerificationUnavailable) as raised:
        _load(handler)

    rendered = f"{raised.value!r}{raised.value.args}"
    for secret in (JWKS_URI, "SECRET-MODULUS", "PROVIDER-TEXT", "LEAKY-CHARSET", "503"):
        assert secret not in rendered
