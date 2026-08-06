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
    """A raw, still unverified ``id_token`` string from the token endpoint."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("id token must be a non-empty string")


def _no_duplicate_members(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    """Refuse a repeated member instead of letting the last value win."""

    seen: dict[str, Any] = {}
    for name, value in pairs:
        if name in seen:
            raise OidcVerificationUnavailable
        seen[name] = value
    return seen


class OidcTokenEndpointClient:
    """Redeem one authorization code at the exactly configured token endpoint.

    Performs no discovery, no JWKS retrieval, no caching, and no ID token
    verification, and does not implement the LQ-157 verifier port.
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
        retried, so the code is never presented twice. Returns the raw ID token,
        ``None`` on a valid OAuth response rejecting the code, and raises
        OidcVerificationUnavailable when no verdict could be reached. No
        provider text, token, or response fragment reaches a return value, an
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
                # Identity encoding keeps the byte cap counting what was sent.
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
                    raise OidcVerificationUnavailable
                self._require_acceptable_headers(response)
                body = self._read_bounded_body(response, started, deadline)
        except OidcVerificationUnavailable:
            raise
        except Exception:
            # Any transport or client fault is a technical failure, never a
            # business rejection.
            raise OidcVerificationUnavailable from None

        self._require_within_deadline(started, deadline)
        return self._result(status, body)

    def _read_clock(self) -> float:
        try:
            moment = self._monotonic()
        except Exception:
            # The clock is a technical dependency and its error text must not
            # escape. BaseException is deliberately not caught.
            raise OidcVerificationUnavailable from None
        # bool is an int subclass and is never a reading.
        if isinstance(moment, bool) or not isinstance(moment, (int, float)):
            raise OidcVerificationUnavailable
        if not math.isfinite(moment):
            raise OidcVerificationUnavailable
        return float(moment)

    def _require_within_deadline(self, started: float, deadline: float) -> None:
        """Bound the total time fail-closed between the I/O steps.

        This is deliberately not a hard preemptive deadline; a clock running
        backwards is unusable rather than fast.
        """

        elapsed = self._read_clock() - started
        if elapsed < 0 or elapsed >= deadline:
            raise OidcVerificationUnavailable

    def _require_acceptable_headers(self, response: httpx2.Response) -> None:
        encoding = response.headers.get("content-encoding")
        if encoding is not None and encoding.strip().lower() != _CONTENT_ENCODING:
            raise OidcVerificationUnavailable

        # A missing header yields "", which is not the accepted media type.
        media_type, _, parameters = response.headers.get("content-type", "").partition(
            ";"
        )
        if media_type.strip().lower() != _MEDIA_TYPE:
            raise OidcVerificationUnavailable
        for parameter in parameters.split(";"):
            # A parameter without a value yields "", which is not the charset.
            name, _, value = parameter.partition("=")
            if (
                name.strip().lower() == "charset"
                and value.strip().strip('"').lower() != _CHARSET
            ):
                raise OidcVerificationUnavailable

        # A missing header yields "0", which is within every limit. The ASCII
        # guard keeps the rule self-contained: isdigit alone accepts full-width
        # digits that int() would then happily convert.
        declared = response.headers.get("content-length", "0").strip(" \t")
        if not (declared.isascii() and declared.isdigit()):
            raise OidcVerificationUnavailable
        if int(declared) > self._policy.token_response_max_bytes:
            raise OidcVerificationUnavailable

    def _read_bounded_body(
        self, response: httpx2.Response, started: float, deadline: float
    ) -> bytes:
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_raw(_READ_CHUNK_BYTES):
            total += len(chunk)
            if total > self._policy.token_response_max_bytes:
                raise OidcVerificationUnavailable
            chunks.append(chunk)
            self._require_within_deadline(started, deadline)
        return b"".join(chunks)

    def _result(self, status: int, body: bytes) -> OidcIdToken | None:
        """Decode the body strictly and classify it on key presence.

        A null, empty, or otherwise falsy value still makes a mixed answer
        structurally unusable, so the value itself is never inspected.
        """

        try:
            payload = json.loads(
                body.decode("utf-8"), object_pairs_hook=_no_duplicate_members
            )
        except (UnicodeDecodeError, ValueError):
            raise OidcVerificationUnavailable from None
        if not isinstance(payload, dict):
            raise OidcVerificationUnavailable

        if status == 200:
            id_token = payload.get("id_token")
            if "error" in payload or not isinstance(id_token, str) or not id_token:
                raise OidcVerificationUnavailable
            # Access and refresh token, token type, and scope are ignored.
            return OidcIdToken(id_token)

        error = payload.get("error")
        if "id_token" in payload or not isinstance(error, str) or not error:
            raise OidcVerificationUnavailable
        # error_description and error_uri never leave this method.
        return None
