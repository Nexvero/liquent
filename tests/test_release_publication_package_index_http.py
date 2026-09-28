import base64
import json
from datetime import timedelta

import httpx2
import pytest

from liquent_platform.identity.release_publication_provider import (
    PackageIndexHttpPolicy,
    PackageIndexProviderConfiguration,
    ReleasePublicationProviderUnavailable,
)
from liquent_platform.transport.package_index import (
    HttpPackageIndexProviderTransport,
)
from test_release_publication_package_index import ARTIFACTS, TARGET


CONFIGURATION = PackageIndexProviderConfiguration(
    "https://packages.example.test", "stable", "secret-token-268"
)
POLICY = PackageIndexHttpPolicy(
    timedelta(seconds=2), timedelta(seconds=5), timedelta(seconds=10),
    response_max_bytes=4096, request_max_bytes=65536,
)
JSON_HEADERS = {"content-type": "application/json"}


def _run(handler, operation="inspect", *, policy=POLICY, clock=None, seen=None):
    def wrapped(request):
        response = handler(request)
        if seen is not None:
            seen.append((request, response))
        return response
    with httpx2.Client(
        transport=httpx2.MockTransport(wrapped),
        cookies={"must-not-leak": "cookie"},
    ) as client:
        arguments = {"monotonic": clock} if clock is not None else {}
        transport = HttpPackageIndexProviderTransport(client, policy, **arguments)
        if operation == "inspect":
            return transport.inspect_package(CONFIGURATION, TARGET)
        return transport.create_package(
            CONFIGURATION, TARGET, ARTIFACTS, "idempotency-268"
        )


def _response(status, body=b"", headers=None):
    content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return lambda request: httpx2.Response(
        status, headers=headers or JSON_HEADERS, content=iter([content])
    )


def test_inspection_uses_one_exact_credentialed_get_and_closes_response():
    seen = []
    body = {
        "canonical_artifact_id": "artifact-268",
        "provider_revision": "revision-268",
        "package_name": "liquent",
        "package_version": "1.2.3",
        "wheel_sha256": "b" * 64,
        "visible": True,
    }
    result = _run(_response(200, body), seen=seen)
    assert result.canonical_artifact_id == "artifact-268"
    assert len(seen) == 1
    request, response = seen[0]
    assert request.method == "GET"
    assert str(request.url) == (
        "https://packages.example.test/v1/targets/stable/liquent/1.2.3"
    )
    assert request.headers["authorization"] == "Bearer secret-token-268"
    assert request.headers["accept-encoding"] == "identity"
    assert "cookie" not in request.headers
    assert request.extensions["timeout"] == {
        "connect": 2.0, "read": 5.0, "write": 10.0, "pool": 10.0,
    }
    assert response.is_closed


def test_only_empty_404_is_confirmed_absence():
    assert _run(_response(404, b"", headers={})) is None
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(_response(404, b"provider detail", headers={}))


@pytest.mark.parametrize("status", [301, 302, 401, 403, 409, 429, 500, 503])
def test_all_other_inspection_statuses_are_technical_unavailability(status):
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(_response(status, {"error": "provider detail"}))


def test_create_uses_one_create_only_put_with_exact_idempotency_and_payload():
    seen = []
    result = _run(
        _response(201, {"provider_request_id": "request-268"}),
        operation="create", seen=seen,
    )
    assert result.provider_request_id == "request-268"
    request, response = seen[0]
    assert request.method == "PUT"
    assert request.headers["if-none-match"] == "*"
    assert request.headers["idempotency-key"] == "idempotency-268"
    assert request.headers["authorization"] == "Bearer secret-token-268"
    body = json.loads(request.content)
    assert set(body) == {
        "bundle_filename", "bundle", "signature", "promotion_evidence",
        "bundle_sha256", "wheel_sha256", "checksums_sha256",
        "signature_sha256", "promotion_evidence_sha256",
    }
    assert base64.b64decode(body["bundle"]) == ARTIFACTS.artifacts.bundle
    assert base64.b64decode(body["signature"]) == ARTIFACTS.artifacts.signature
    assert response.is_closed


@pytest.mark.parametrize("status", [200, 202, 204, 400, 401, 409, 429, 500])
def test_only_201_is_a_create_acknowledgement(status):
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(
            _response(status, {"provider_request_id": "request-268"}),
            operation="create",
        )


@pytest.mark.parametrize("body", [
    b"not-json",
    b"[]",
    b'{"provider_request_id":"a","provider_request_id":"b"}',
    b'{"provider_request_id":"a","extra":true}',
    b'{"provider_request_id":""}',
])
def test_create_response_is_strict_and_duplicate_free(body):
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(_response(201, body), operation="create")


@pytest.mark.parametrize("headers", [
    {},
    {"content-type": "text/html"},
    {"content-type": "application/json", "content-encoding": "gzip"},
    {"content-type": "application/json", "content-length": "+10"},
    {"content-type": "application/json; charset=iso-8859-1"},
])
def test_noncanonical_response_framing_is_rejected(headers):
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(_response(200, {}, headers=headers))


def test_response_is_bounded_incrementally_and_never_retried():
    produced = 0
    def handler(request):
        def stream():
            nonlocal produced
            for _ in range(100):
                produced += 1
                yield b"x" * 512
        return httpx2.Response(200, headers=JSON_HEADERS, content=stream())
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(handler)
    assert produced < 20


def test_declared_oversize_is_rejected_before_body_read():
    produced = 0
    def handler(request):
        def stream():
            nonlocal produced
            produced += 1
            yield b"{}"
        return httpx2.Response(
            200, headers={**JSON_HEADERS, "content-length": "4097"},
            content=stream(),
        )
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(handler)
    assert produced == 0


def test_request_size_is_checked_before_transport():
    seen = []
    tiny = PackageIndexHttpPolicy(
        timedelta(seconds=1), timedelta(seconds=1), timedelta(seconds=2),
        response_max_bytes=100, request_max_bytes=10,
    )
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(_response(201, {}), operation="create", policy=tiny, seen=seen)
    assert seen == []


def test_transport_fault_and_deadline_are_detail_free():
    def broken(request):
        raise httpx2.ConnectError("secret endpoint detail")
    with pytest.raises(ReleasePublicationProviderUnavailable) as raised:
        _run(broken)
    assert raised.value.args == ("release_publication_provider_unavailable",)
    assert raised.value.__cause__ is None
    readings = iter([0.0, 10.0])
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(_response(200, {}), clock=lambda: next(readings))
    backwards = iter([5.0, 6.0, 5.5])
    with pytest.raises(ReleasePublicationProviderUnavailable):
        _run(_response(200, {}), clock=lambda: next(backwards))


def test_policy_is_positive_bounded_and_repr_does_not_expose_configuration():
    assert repr(HttpPackageIndexProviderTransport) != repr(CONFIGURATION)
    with pytest.raises(ValueError):
        PackageIndexHttpPolicy(
            timedelta(0), timedelta(seconds=1), timedelta(seconds=2), 1, 1
        )
    with pytest.raises(ValueError):
        PackageIndexHttpPolicy(
            timedelta(seconds=3), timedelta(seconds=1), timedelta(seconds=2), 1, 1
        )
