"""One controlled server-side authorization code exchange, nothing more."""

import json
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx2

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy


_MEDIA_TYPE = "application/json"
_CONTENT_ENCODING = "identity"
_CHARSET = "utf-8"
_OAUTH_ERROR_STATUSES = frozenset({400, 401})
_READ_CHUNK_BYTES = 8192


@dataclass(frozen=True, slots=True)
class OidcIdToken:
    """A raw, still unverified ``id_token`` string from the token endpoint.

    Holding one means only that the endpoint returned a string called
    ``id_token``; it is not evidence that the token is valid or trustworthy.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("id token must be a non-empty string")


def _no_duplicate_members(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    # A repeated id_token or error would otherwise be decided by the parser's
    # last-value-wins convention instead of by this contract.
    seen: dict[str, Any] = {}
    for name, value in pairs:
        if name in seen:
            raise OidcVerificationUnavailable
        seen[name] = value
    return seen


class OidcTokenEndpointClient:
    """Redeem one authorization code at the exactly configured token endpoint.

    Performs no discovery, no JWKS retrieval, no caching, and no ID token
    verification, and does not implement the LQ-157 verifier port. ``monotonic``
    only bounds the total time measurably; it is never a calendar clock.
    """

    def __init__(
        self,
        client: httpx2.Client,
        policy: OidcVerificationPolicy,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._policy = policy
        self._monotonic = monotonic

    def exchange_authorization_code(
        self,
        configuration: TrustedOidcClientConfiguration,
        verification: OidcAuthorizationCodeVerification,
    ) -> OidcIdToken | None:
        """Exchange the code exactly once and return the raw ID token.

        Exactly one POST is issued, redirects are never followed, and nothing is
        retried: a timeout, network fault, 5xx, malformed response, or code
        rejection all end the call, so the code is never presented twice.

        Returns the raw ID token on success, ``None`` on a valid OAuth error
        response rejecting the code, and raises OidcVerificationUnavailable when
        no verdict could be reached. No provider text, token, or response body
        reaches a return value, an exception, or a log.
        """

        deadline = self._policy.total_timeout.total_seconds()
        started = self._read_clock()

        try:
            with self._client.stream(
                "POST",
                configuration.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": verification.authorization_code,
                    "redirect_uri": verification.redirect_uri,
                    "client_id": configuration.client_id,
                    "code_verifier": verification.code_verifier,
                },
                # No transparent compression, so the byte cap counts what the
                # peer actually sent.
                headers={"Accept": _MEDIA_TYPE, "Accept-Encoding": _CONTENT_ENCODING},
                follow_redirects=False,
                timeout=httpx2.Timeout(
                    connect=self._policy.connect_timeout.total_seconds(),
                    read=self._policy.read_timeout.total_seconds(),
                    write=deadline,
                    pool=deadline,
                ),
            ) as response:
                self._require_within_deadline(started, deadline)
                status = response.status_code
                if status != 200 and status not in _OAUTH_ERROR_STATUSES:
                    # Redirects, 5xx, and anything else are technical faults; a
                    # redirect in particular is never followed.
                    raise OidcVerificationUnavailable
                self._require_acceptable_headers(response)
                body = self._read_bounded_body(response, started, deadline)
        except OidcVerificationUnavailable:
            raise
        except Exception:
            # Network, TLS, connect, read, write, pool, timeout, and any
            # unexpected client fault: never a business rejection.
            raise OidcVerificationUnavailable from None

        self._require_within_deadline(started, deadline)
        return self._result(status, body)

    def _read_clock(self) -> float:
        try:
            moment = self._monotonic()
        except OidcVerificationUnavailable:
            raise
        except Exception:
            # An injected clock is a technical dependency and its error text
            # must not escape. BaseException is deliberately not caught.
            raise OidcVerificationUnavailable from None
        # bool is an int subclass and is never a reading.
        if isinstance(moment, bool) or not isinstance(moment, (int, float)):
            raise OidcVerificationUnavailable
        if not math.isfinite(moment):
            raise OidcVerificationUnavailable
        return float(moment)

    def _require_within_deadline(self, started: float, deadline: float) -> None:
        """Bound the total time fail-closed between the I/O steps.

        With a synchronous client this is deliberately not a claim that a thread
        already blocked inside an I/O call is interrupted; the per-phase client
        timeouts cover that part. A clock running backwards is unusable, not
        fast.
        """

        elapsed = self._read_clock() - started
        if elapsed < 0 or elapsed >= deadline:
            raise OidcVerificationUnavailable

    def _require_acceptable_headers(self, response: httpx2.Response) -> None:
        encoding = response.headers.get("content-encoding")
        if encoding is not None and encoding.strip().lower() != _CONTENT_ENCODING:
            # Any other coding would let a small transfer expand past the cap.
            raise OidcVerificationUnavailable

        content_type = response.headers.get("content-type")
        if content_type is None:
            raise OidcVerificationUnavailable
        media_type, _, parameters = content_type.partition(";")
        if media_type.strip().lower() != _MEDIA_TYPE:
            raise OidcVerificationUnavailable
        for parameter in parameters.split(";"):
            name, assigned, value = parameter.partition("=")
            if name.strip().lower() != "charset":
                continue
            # Only UTF-8 is accepted; the body decoder has no fallback, so an
            # unusable charset parameter is refused rather than ignored.
            if not assigned or value.strip().strip('"').lower() != _CHARSET:
                raise OidcVerificationUnavailable

        declared = response.headers.get("content-length")
        if declared is None:
            return
        digits = declared.strip(" \t")
        # ASCII digits only: "+10", "-1", "1.0", "10, 10", non-ASCII digits, and
        # an empty value are unusable rather than tolerated.
        if not digits or not all("0" <= character <= "9" for character in digits):
            raise OidcVerificationUnavailable
        if int(digits) > self._policy.token_response_max_bytes:
            raise OidcVerificationUnavailable

    def _read_bounded_body(
        self, response: httpx2.Response, started: float, deadline: float
    ) -> bytes:
        limit = self._policy.token_response_max_bytes
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_raw(_READ_CHUNK_BYTES):
            total += len(chunk)
            if total > limit:
                raise OidcVerificationUnavailable
            chunks.append(chunk)
            self._require_within_deadline(started, deadline)
        return b"".join(chunks)

    def _result(self, status: int, body: bytes) -> OidcIdToken | None:
        try:
            payload = json.loads(
                body.decode("utf-8"), object_pairs_hook=_no_duplicate_members
            )
        except OidcVerificationUnavailable:
            raise
        except (UnicodeDecodeError, ValueError):
            raise OidcVerificationUnavailable from None
        if not isinstance(payload, dict):
            raise OidcVerificationUnavailable

        # Classified on key presence: a null, empty, or otherwise falsy value
        # still makes the answer mixed and therefore structurally unusable.
        if status == 200:
            if "error" in payload:
                raise OidcVerificationUnavailable
            id_token = payload.get("id_token")
            if not isinstance(id_token, str) or not id_token:
                raise OidcVerificationUnavailable
            # Access and refresh token, token type, and scope are ignored.
            return OidcIdToken(id_token)

        # A valid OAuth rejection of the single-use code; error_description and
        # error_uri deliberately never leave this method.
        if "id_token" in payload:
            raise OidcVerificationUnavailable
        error = payload.get("error")
        if not isinstance(error, str) or not error:
            raise OidcVerificationUnavailable
        return None
