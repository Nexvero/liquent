"""One controlled server-side JWKS retrieval, nothing more."""

import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx2

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_verification import OidcVerificationUnavailable
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy


_MEDIA_TYPE = "application/json"
_CONTENT_ENCODING = "identity"
_CHARSET = "utf-8"
_READ_CHUNK_BYTES = 8192
# Credentials a preconfigured client would otherwise lend to this request.
_CREDENTIAL_HEADERS = ("cookie", "authorization")


def _no_duplicate_members(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    """Refuse a repeated member instead of letting the last value win."""

    seen: dict[str, Any] = {}
    for name, value in pairs:
        if name in seen:
            raise OidcVerificationUnavailable
        seen[name] = value
    return seen


class OidcJwksEndpointClient:
    """Load one trusted key set from the exactly configured ``jwks_uri``.

    Performs no discovery, no caching, no key selection, and no ID token
    verification, and does not implement the LQ-157 verifier port. Token-supplied
    key sources such as ``jku``, ``x5u``, and ``jwk`` are never read here: the
    URL comes from trusted configuration alone.
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

    def load_jwks(
        self, configuration: TrustedOidcClientConfiguration
    ) -> Mapping[str, object]:
        """Fetch the key set exactly once and return it structurally checked.

        Exactly one GET is built and sent, redirects are never followed, and
        nothing is retried. A preconfigured client lends this request no cookie
        and no Authorization header. Only HTTP 200 is usable; every other
        status, and every network, framing, decoding, or structural fault,
        raises OidcVerificationUnavailable. The parsed document is returned as
        it was read: no normalization, reordering, or per-entry reconstruction,
        so a later verifier sees exactly what the trusted source published.

        No URL, header value, response fragment, provider text, or key material
        reaches a return value, an exception, or a log.
        """

        deadline = self._policy.total_timeout.total_seconds()
        # The last accepted reading lives only inside this call, so no clock
        # state survives between two retrievals.
        started = self._read_clock(None)
        last = [started]

        try:
            request = self._client.build_request(
                "GET",
                configuration.jwks_uri,
                # No request body: a public key set is fetched, not created.
                headers={"Accept": _MEDIA_TYPE, "Accept-Encoding": _CONTENT_ENCODING},
                timeout=httpx2.Timeout(
                    connect=self._policy.connect_timeout.total_seconds(),
                    read=self._policy.read_timeout.total_seconds(),
                    write=deadline,
                    pool=deadline,
                ),
            )
            # Removed rather than blanked, so the headers are absent entirely.
            # auth=None below stops the client's own scheme from adding one.
            for inherited in _CREDENTIAL_HEADERS:
                if inherited in request.headers:
                    del request.headers[inherited]

            response = self._client.send(
                request, stream=True, follow_redirects=False, auth=None
            )
            try:
                self._require_within_deadline(started, last, deadline)
                if response.status_code != 200:
                    # Redirects, 304, 4xx, and 5xx alike: no key set was served.
                    raise OidcVerificationUnavailable
                self._require_acceptable_headers(response)
                body = self._read_bounded_body(response, started, last, deadline)
            finally:
                response.close()
        except OidcVerificationUnavailable:
            raise
        except Exception:
            # Any transport or client fault is a technical failure.
            raise OidcVerificationUnavailable from None

        self._require_within_deadline(started, last, deadline)
        key_set = self._parsed_key_set(body)
        # Decoding, parsing, and the shape checks take time too, so the bound
        # is confirmed once more immediately before returning.
        self._require_within_deadline(started, last, deadline)
        return key_set

    def _read_clock(self, previous: float | None) -> float:
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
        reading = float(moment)
        # A monotonic clock never steps back, not even between two later reads
        # that both sit above the start. A tie is still fine.
        if previous is not None and reading < previous:
            raise OidcVerificationUnavailable
        return reading

    def _require_within_deadline(
        self, started: float, last: list[float], deadline: float
    ) -> None:
        """Bound the total time fail-closed between the steps.

        This is deliberately not a hard preemptive deadline. Because every
        reading is checked against the previous one, the elapsed time can never
        be negative here; a clock that steps back has already been refused.
        """

        last[0] = self._read_clock(last[0])
        if last[0] - started >= deadline:
            raise OidcVerificationUnavailable

    def _require_acceptable_headers(self, response: httpx2.Response) -> None:
        encoding = response.headers.get("content-encoding")
        if encoding is not None and encoding.strip().lower() != _CONTENT_ENCODING:
            # Decompression could expand a small transfer past the byte cap.
            raise OidcVerificationUnavailable

        # A missing header yields "", which is not the accepted media type.
        media_type, _, parameters = response.headers.get("content-type", "").partition(
            ";"
        )
        if media_type.strip().lower() != _MEDIA_TYPE:
            raise OidcVerificationUnavailable
        for parameter in parameters.split(";"):
            name, _, value = parameter.partition("=")
            if name.strip().lower() != "charset":
                continue
            candidate = value.strip()
            # Exactly one optional quote pair. Stripping every quote instead
            # would turn `"utf-8`, `utf-8"`, and `""utf-8""` into a charset
            # nobody declared, and a parameter without a value stays "".
            if len(candidate) > 1 and candidate[0] == '"' and candidate[-1] == '"':
                candidate = candidate[1:-1]
            if candidate.lower() != _CHARSET:
                raise OidcVerificationUnavailable

        # A missing header yields "0", which is within every limit. The ASCII
        # guard keeps the rule self-contained: isdigit alone accepts full-width
        # digits that int() would then happily convert.
        declared = response.headers.get("content-length", "0").strip(" \t")
        if not (declared.isascii() and declared.isdigit()):
            raise OidcVerificationUnavailable
        if int(declared) > self._policy.jwks_response_max_bytes:
            raise OidcVerificationUnavailable

    def _read_bounded_body(
        self,
        response: httpx2.Response,
        started: float,
        last: list[float],
        deadline: float,
    ) -> bytes:
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_raw(_READ_CHUNK_BYTES):
            total += len(chunk)
            # Counted cumulatively, so an under-reported length cannot buy an
            # unbounded read.
            if total > self._policy.jwks_response_max_bytes:
                raise OidcVerificationUnavailable
            chunks.append(chunk)
            self._require_within_deadline(started, last, deadline)
        return b"".join(chunks)

    def _parsed_key_set(self, body: bytes) -> Mapping[str, object]:
        """Decode strictly once and accept only a usable key set shape.

        Nothing beyond the shape is judged here: ``kid``, ``kty``, ``crv``,
        ``use``, ``key_ops``, and ``alg`` stay the offline verifier's business,
        and no JWK is constructed.
        """

        try:
            document = json.loads(
                body.decode("utf-8"), object_pairs_hook=_no_duplicate_members
            )
            if not isinstance(document, dict):
                raise OidcVerificationUnavailable
            keys = document.get("keys")
            # json.loads yields a list for a JSON array and a dict for an object.
            if not isinstance(keys, list):
                raise OidcVerificationUnavailable
            if not all(isinstance(entry, dict) for entry in keys):
                raise OidcVerificationUnavailable
        except OidcVerificationUnavailable:
            raise
        except Exception:
            # Invalid UTF-8, JSON syntax, a RecursionError from deep nesting,
            # and any other normal parser fault become the same neutral answer.
            # BaseException is deliberately not caught.
            raise OidcVerificationUnavailable from None
        return document
