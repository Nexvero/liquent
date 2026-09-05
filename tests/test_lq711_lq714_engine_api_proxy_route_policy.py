import json
from urllib.parse import urlencode

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import (
    ClosedManifestHandoffSupervisorEngineApiRoutePolicy,
    ManifestHandoffSupervisorEngineApiOperation,
)


POLICY = ClosedManifestHandoffSupervisorEngineApiRoutePolicy()
CONTAINER = "a" * 64


def _find(creation="creation-711"):
    filters = json.dumps(
        {"label": [f"liquent.supervisor.creation={creation}"]},
        sort_keys=True, separators=(",", ":"),
    )
    return "/v1.45/containers/json?" + urlencode({"all": "1", "filters": filters})


@pytest.mark.parametrize(
    ("method", "target", "body", "operation"),
    (
        ("GET", _find(), None, ManifestHandoffSupervisorEngineApiOperation.FIND),
        ("POST", "/v1.45/containers/create", b"{}", ManifestHandoffSupervisorEngineApiOperation.CREATE),
        ("GET", f"/v1.45/containers/{CONTAINER}/json", None, ManifestHandoffSupervisorEngineApiOperation.INSPECT),
        ("POST", f"/v1.45/containers/{CONTAINER}/start", b"", ManifestHandoffSupervisorEngineApiOperation.START),
        ("POST", f"/v1.45/containers/{CONTAINER}/wait?condition=not-running", b"", ManifestHandoffSupervisorEngineApiOperation.WAIT),
        ("POST", f"/v1.45/containers/{CONTAINER}/stop?t=10", b"", ManifestHandoffSupervisorEngineApiOperation.STOP),
        ("POST", f"/v1.45/containers/{CONTAINER}/kill?signal=KILL", b"", ManifestHandoffSupervisorEngineApiOperation.KILL),
    ),
)
def test_exact_client_routes_are_classified(method, target, body, operation) -> None:
    result = POLICY.authorize(method, target, body)
    assert result.operation is operation


@pytest.mark.parametrize(
    ("method", "target", "body"),
    (
        ("DELETE", f"/v1.45/containers/{CONTAINER}", b""),
        ("POST", f"/v1.45/containers/{CONTAINER}/exec", b"{}"),
        ("GET", f"/v1.45/containers/{CONTAINER}/logs", None),
        ("POST", "/v1.45/images/create", b"{}"),
        ("POST", "/v1.45/build", b"x"),
        ("GET", "/v1.44/containers/json", None),
        ("GET", _find() + "&extra=1", None),
        ("GET", _find("bad value"), None),
        ("GET", f"/v1.45/containers/{'A' * 64}/json", None),
        ("POST", f"/v1.45/containers/{CONTAINER}/stop?t=11", b""),
        ("POST", f"/v1.45/containers/{CONTAINER}/kill?signal=TERM", b""),
        ("POST", "/v1.45/containers/create", b""),
    ),
)
def test_every_route_or_query_expansion_fails_detail_free(method, target, body) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        POLICY.authorize(method, target, body)
    assert str(caught.value) == "manifest_handoff_registry_unavailable"


def test_request_and_target_bounds_fail_closed() -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        POLICY.authorize("POST", "/v1.45/containers/create", b"x" * 65_537)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        POLICY.authorize("GET", "/" + "x" * 4097, None)


def test_create_route_classification_is_not_forwarding_authority() -> None:
    result = POLICY.authorize("POST", "/v1.45/containers/create", b"{}")
    assert result.operation is ManifestHandoffSupervisorEngineApiOperation.CREATE
    assert not hasattr(POLICY, "forward")
    assert not hasattr(POLICY, "connect")
    assert not hasattr(POLICY, "listen")
