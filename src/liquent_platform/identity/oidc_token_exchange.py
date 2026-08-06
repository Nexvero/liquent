"""One controlled server-side authorization code exchange, nothing more."""

import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx2

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy


_ACCEPTED_MEDIA_TYPE = "application/json"
_ACCEPTED_CONTENT_ENCODING = "identity"
_OAUTH_ERROR_STATUSES = frozenset({400, 401})
_READ_CHUNK_BYTES = 8192


@dataclass(frozen=True, slots=True)
class OidcIdToken:
    """A raw, still unverified ``id_token`` string from the token endpoint.

    Holding one means only that the endpoint returned a string called
    ``id_token``; it is not evidence that the token is valid or trustworthy.
    The value is hidden from ``repr`` and kept verbatim.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("id token must be a non-empty string")


class OidcTokenEndpointClient:
    """Redeem one authorization code at the exactly configured token endpoint.

    Performs no discovery, no JWKS retrieval, no caching, and no ID token
    verification, and it does not implement the LQ-157 verifier port.

    ``monotonic`` exists only to bound the total time measurably and to keep
    that bound testable; it is never a calendar clock.
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

        Exactly one POST is issued. Redirects are never followed, nothing is
        retried, and the code is never presented twice: a timeout, network
        fault, 5xx, malformed response, or code rejection all end the call.

        Returns the raw ID token on a successful exchange, ``None`` on a valid
        OAuth error response rejecting the code, and raises
        OidcVerificationUnavailable when no verdict could be reached. No
        provider text, token, or response body reaches a return value, an
        exception, or a log.
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
                headers={
                    "Accept": _ACCEPTED_MEDIA_TYPE,
                    # No transparent compression, so the byte cap below counts
                    # what the peer actually sent.
                    "Accept-Encoding": _ACCEPTED_CONTENT_ENCODING,
                },
                follow_redirects=False,
                timeout=self._timeout(),
            ) as response:
                self._require_within_deadline(started, deadline)
                status = response.status_code
                if status not in _OAUTH_ERROR_STATUSES and status != 200:
                    # Redirects, 5xx, and anything else are technical faults;
                    # a redirect in particular is never followed.
                    raise OidcVerificationUnavailable
                self._require_acceptable_encoding(response)
                self._require_declared_length_within_limit(response)
                body = self._read_bounded_body(response, started, deadline)
        except OidcVerificationUnavailable:
            raise
        except httpx2.HTTPError:
            # Network, TLS, connect, read, write, pool, and timeout faults.
            raise OidcVerificationUnavailable from None
        except Exception:
            raise OidcVerificationUnavailable from None

        self._require_within_deadline(started, deadline)
        payload = self._decode_json_object(body)
        return self._result(status, payload)

    # -- request shaping ----------------------------------------------------

    def _timeout(self) -> httpx2.Timeout:
        overall = self._policy.total_timeout.total_seconds()
        return httpx2.Timeout(
            connect=self._policy.connect_timeout.total_seconds(),
            read=self._policy.read_timeout.total_seconds(),
            # Write and pool are bounded by the overall limit; no value ever
            # comes from a provider response.
            write=overall,
            pool=overall,
        )

    # -- time ---------------------------------------------------------------

    def _read_clock(self) -> float:
        moment = self._monotonic()
        # bool is an int subclass and is never a reading.
        if isinstance(moment, bool) or not isinstance(moment, (int, float)):
            raise OidcVerificationUnavailable
        if not math.isfinite(moment):
            raise OidcVerificationUnavailable
        return float(moment)

    def _require_within_deadline(self, started: float, deadline: float) -> None:
        """Fail closed between I/O steps.

        This bounds the total time at each step boundary. With a synchronous
        client it is deliberately not a claim that a thread already blocked
        inside an I/O call is interrupted; the per-phase client timeouts cover
        that part.
        """

        if self._read_clock() - started >= deadline:
            raise OidcVerificationUnavailable

    # -- response bounds ----------------------------------------------------

    def _require_acceptable_encoding(self, response: httpx2.Response) -> None:
        encoding = response.headers.get("content-encoding")
        if encoding is not None and encoding.strip().lower() != _ACCEPTED_CONTENT_ENCODING:
            # Any other coding would let a small transfer expand past the cap.
            raise OidcVerificationUnavailable

        content_type = response.headers.get("content-type")
        if content_type is None:
            raise OidcVerificationUnavailable
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != _ACCEPTED_MEDIA_TYPE:
            raise OidcVerificationUnavailable

    def _require_declared_length_within_limit(self, response: httpx2.Response) -> None:
        declared = response.headers.get("content-length")
        if declared is None:
            return
        try:
            length = int(declared.strip())
        except ValueError:
            raise OidcVerificationUnavailable from None
        if length < 0 or length > self._policy.token_response_max_bytes:
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

    # -- body ---------------------------------------------------------------

    def _decode_json_object(self, body: bytes) -> dict[str, object]:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise OidcVerificationUnavailable from None
        if not isinstance(payload, dict):
            raise OidcVerificationUnavailable
        return payload

    def _result(self, status: int, payload: dict[str, object]) -> OidcIdToken | None:
        id_token = payload.get("id_token")
        error = payload.get("error")

        if status == 200:
            if error is not None:
                # A mixed answer is never treated as a success.
                raise OidcVerificationUnavailable
            if not isinstance(id_token, str) or not id_token:
                raise OidcVerificationUnavailable
            # Access token, refresh token, token type, and scope are ignored
            # and never stored.
            return OidcIdToken(id_token)

        # A valid OAuth rejection of the single-use code.
        if id_token is not None:
            raise OidcVerificationUnavailable
        if not isinstance(error, str) or not error:
            raise OidcVerificationUnavailable
        # error_description and error_uri deliberately never leave this method.
        return None
