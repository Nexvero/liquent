"""One bounded HTTPS transport for the controlled package-index adapter."""

from __future__ import annotations

import base64
import json
import math
import time
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import quote

import httpx2

from liquent_platform.identity.release_publication import (
    ReleasePublicationTarget,
    VerifiedReleasePublicationArtifacts,
)
from liquent_platform.identity.release_publication_provider import (
    PackageIndexArtifactRecord,
    PackageIndexCreateRecord,
    PackageIndexHttpPolicy,
    PackageIndexProviderConfiguration,
    ReleasePublicationProviderUnavailable,
)


_JSON = "application/json"
_IDENTITY = "identity"
_CHUNK = 8192


def _members(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ReleasePublicationProviderUnavailable
        result[name] = value
    return result


class HttpPackageIndexProviderTransport:
    """Issue exactly one bounded request per inspect or immutable create."""

    __slots__ = ("_client", "_policy", "_monotonic")

    def __init__(
        self,
        client: httpx2.Client,
        policy: PackageIndexHttpPolicy,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if type(policy) is not PackageIndexHttpPolicy:
            raise ReleasePublicationProviderUnavailable
        self._client = client
        self._policy = policy
        self._monotonic = monotonic

    def __repr__(self) -> str:
        return "HttpPackageIndexProviderTransport()"

    def inspect_package(self, configuration, target):
        self._require_inputs(configuration, target)
        status, body = self._request(
            "GET", self._url(configuration, target), configuration, None, {}
        )
        if status == 404:
            if body:
                raise ReleasePublicationProviderUnavailable
            return None
        if status != 200:
            raise ReleasePublicationProviderUnavailable
        payload = self._json(body, {
            "canonical_artifact_id", "provider_revision", "package_name",
            "package_version", "wheel_sha256", "visible",
        })
        try:
            return PackageIndexArtifactRecord(
                payload["canonical_artifact_id"], payload["provider_revision"],
                payload["package_name"], payload["package_version"],
                payload["wheel_sha256"], payload["visible"],
            )
        except Exception:
            raise ReleasePublicationProviderUnavailable from None

    def create_package(
        self, configuration, target, artifacts, idempotency_key,
    ):
        self._require_inputs(configuration, target)
        if (
            type(artifacts) is not VerifiedReleasePublicationArtifacts
            or type(idempotency_key) is not str
            or not idempotency_key
            or any(ord(character) < 32 or ord(character) == 127 for character in idempotency_key)
        ):
            raise ReleasePublicationProviderUnavailable
        body = json.dumps({
            "bundle_filename": artifacts.artifacts.bundle_filename,
            "bundle": base64.b64encode(artifacts.artifacts.bundle).decode("ascii"),
            "signature": base64.b64encode(artifacts.artifacts.signature).decode("ascii"),
            "promotion_evidence": base64.b64encode(
                artifacts.artifacts.promotion_evidence
            ).decode("ascii"),
            "bundle_sha256": artifacts.bundle_sha256,
            "wheel_sha256": artifacts.wheel_sha256,
            "checksums_sha256": artifacts.checksums_sha256,
            "signature_sha256": artifacts.signature_sha256,
            "promotion_evidence_sha256": artifacts.promotion_evidence_sha256,
        }, sort_keys=True, separators=(",", ":")).encode("ascii")
        if len(body) > self._policy.request_max_bytes:
            raise ReleasePublicationProviderUnavailable
        status, response = self._request(
            "PUT", self._url(configuration, target), configuration, body,
            {"Content-Type": _JSON, "If-None-Match": "*", "Idempotency-Key": idempotency_key},
        )
        if status != 201:
            raise ReleasePublicationProviderUnavailable
        payload = self._json(response, {"provider_request_id"})
        try:
            return PackageIndexCreateRecord(payload["provider_request_id"])
        except Exception:
            raise ReleasePublicationProviderUnavailable from None

    @staticmethod
    def _require_inputs(configuration, target):
        if (
            type(configuration) is not PackageIndexProviderConfiguration
            or type(target) is not ReleasePublicationTarget
        ):
            raise ReleasePublicationProviderUnavailable

    @staticmethod
    def _url(configuration, target):
        segments = (target.target_name, target.package_name, target.package_version)
        encoded = "/".join(quote(value, safe="") for value in segments)
        return f"{configuration.origin}/v1/targets/{encoded}"

    def _request(self, method, url, configuration, body, extra_headers):
        deadline = self._policy.total_timeout.total_seconds()
        started = self._clock()
        last = [started]
        headers = {
            "Accept": _JSON,
            "Accept-Encoding": _IDENTITY,
            "Authorization": f"Bearer {configuration.credential}",
            **extra_headers,
        }
        try:
            request = self._client.build_request(
                method, url, content=body, headers=headers,
                timeout=httpx2.Timeout(
                    connect=self._policy.connect_timeout.total_seconds(),
                    read=self._policy.read_timeout.total_seconds(),
                    write=deadline, pool=deadline,
                ),
            )
            if "cookie" in request.headers:
                del request.headers["cookie"]
            response = self._client.send(
                request, stream=True, follow_redirects=False, auth=None
            )
            try:
                self._deadline(started, last, deadline)
                self._headers(response)
                result = self._body(response, started, last, deadline)
                status = response.status_code
            finally:
                response.close()
        except ReleasePublicationProviderUnavailable:
            raise
        except Exception:
            raise ReleasePublicationProviderUnavailable from None
        self._deadline(started, last, deadline)
        return status, result

    def _clock(self, previous=None):
        try:
            value = self._monotonic()
        except Exception:
            raise ReleasePublicationProviderUnavailable from None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ReleasePublicationProviderUnavailable
        result = float(value)
        if previous is not None and result < previous:
            raise ReleasePublicationProviderUnavailable
        return result

    def _deadline(self, started, last, deadline):
        last[0] = self._clock(last[0])
        if last[0] - started >= deadline:
            raise ReleasePublicationProviderUnavailable

    def _headers(self, response):
        encoding = response.headers.get("content-encoding")
        if encoding is not None and encoding.strip().lower() != _IDENTITY:
            raise ReleasePublicationProviderUnavailable
        declared = response.headers.get("content-length", "0").strip(" \t")
        if not (declared.isascii() and declared.isdigit()):
            raise ReleasePublicationProviderUnavailable
        if int(declared) > self._policy.response_max_bytes:
            raise ReleasePublicationProviderUnavailable
        if response.status_code == 404:
            return
        media, _, parameters = response.headers.get("content-type", "").partition(";")
        if media.strip().lower() != _JSON:
            raise ReleasePublicationProviderUnavailable
        for parameter in parameters.split(";"):
            name, _, value = parameter.partition("=")
            if name.strip().lower() == "charset" and value.strip().strip('"').lower() != "utf-8":
                raise ReleasePublicationProviderUnavailable

    def _body(self, response, started, last, deadline):
        chunks, total = [], 0
        for chunk in response.iter_raw(_CHUNK):
            total += len(chunk)
            if total > self._policy.response_max_bytes:
                raise ReleasePublicationProviderUnavailable
            chunks.append(chunk)
            self._deadline(started, last, deadline)
        return b"".join(chunks)

    @staticmethod
    def _json(body, keys):
        try:
            payload = json.loads(body.decode("utf-8"), object_pairs_hook=_members)
        except ReleasePublicationProviderUnavailable:
            raise
        except Exception:
            raise ReleasePublicationProviderUnavailable from None
        if not isinstance(payload, dict) or set(payload) != keys:
            raise ReleasePublicationProviderUnavailable
        return payload
