import json
from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff_supervisor import ManifestHandoffSupervisorHandleId
from liquent_platform.identity.manifest_handoff_supervisor_engine import ManifestHandoffSupervisorEngineProfile
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import ManifestHandoffSupervisorLaunchDocumentDigest
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import ManifestHandoffSupervisorLaunchDocumentExpectation
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_child_launch_anchor import CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_gate import (
    AuthorizedManifestHandoffSupervisorEngineApiRequest,
    ClosedManifestHandoffSupervisorEngineApiGate,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import (
    AuthorizedManifestHandoffSupervisorEngineApiRoute,
    ClosedManifestHandoffSupervisorCreateRequestPolicy,
    ManifestHandoffSupervisorEngineApiOperation as Operation,
)


ROOT = Path("/srv/liquent/supervisor")
SOURCE = Path("/srv/liquent/source")
TARGET = Path("/srv/liquent/target")
CONTAINER = "a" * 64
IMAGE = "sha256:" + "b" * 64


def gate():
    return ClosedManifestHandoffSupervisorEngineApiGate(
        ClosedManifestHandoffSupervisorCreateRequestPolicy(
            control_root=ROOT, source_root=SOURCE, target_root=TARGET,
            writer_command="writer-wrapper", recovery_command="recovery-wrapper",
            wrapper_uid=10002, wrapper_gid=10003,
        )
    )


def request(method, target, body=None):
    headers = [
        b"host: localhost", b"accept: application/json", b"connection: close",
    ]
    payload = b"" if body is None else body
    if body is not None:
        headers += [b"content-type: application/json",
                    f"content-length: {len(body)}".encode()]
    return (
        f"{method} {target} HTTP/1.1\r\n".encode()
        + b"\r\n".join(headers) + b"\r\n\r\n" + payload
    )


def response(status, body=None):
    headers = []
    payload = b"" if body is None else body
    if body is not None:
        headers = [b"content-type: application/json",
                   f"content-length: {len(body)}".encode()]
    return (
        f"HTTP/1.1 {status} status\r\n".encode()
        + b"\r\n".join(headers) + (b"\r\n\r\n" if headers else b"\r\n")
        + payload
    )


def create_body():
    expectation = ManifestHandoffSupervisorLaunchDocumentExpectation(
        ManifestHandoffSupervisorControlArtifactId("launch-731"),
        ManifestHandoffSupervisorLaunchDocumentDigest("d" * 64),
        ManifestHandoffSupervisorCreationId("creation-731"),
        ManifestHandoffSupervisorHandleId("handle-731"),
        ManifestHandoffSupervisorControlDirectoryId("directory-731"),
        ManifestHandoffSupervisorImageDigest(IMAGE),
        ManifestHandoffSupervisorEngineProfile.WRITER,
    )
    control = ROOT / "job-731"
    value = {
        "Image": IMAGE,
        "Entrypoint": ["writer-wrapper"] + list(
            CanonicalManifestHandoffSupervisorChildLaunchAnchorCodec().encode(expectation)
        ),
        "User": "10002:10003",
        "Labels": {
            "liquent.supervisor.creation": "creation-731",
            "liquent.supervisor.handle": "handle-731",
            "liquent.supervisor.control": "directory-731",
            "liquent.supervisor.launch-document": "launch-731",
            "liquent.supervisor.launch-sha256": "d" * 64,
            "liquent.supervisor.profile": "writer",
        },
        "HostConfig": {
            "AutoRemove": False,
            "Binds": [
                f"{control / 'control-artifacts'}:/run/liquent/control:rw",
                f"{control / 'launch-binding.json'}:/run/liquent/launch/launch-binding.json:ro",
                f"{SOURCE / 'scope'}:/run/liquent/source:ro",
                f"{TARGET / 'scope'}:/run/liquent/target:rw",
            ],
            "CapDrop": ["ALL"], "NetworkMode": "none", "PidMode": "private",
            "Privileged": False, "ReadonlyRootfs": True,
            "RestartPolicy": {"MaximumRetryCount": 0, "Name": "no"},
        },
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_non_create_request_is_bound_without_create_authority() -> None:
    authorized = gate().authorize_request(
        request("GET", f"/v1.45/containers/{CONTAINER}/json")
    )
    assert authorized.route.operation is Operation.INSPECT
    assert authorized.route.container_id == CONTAINER
    assert authorized.create is None


def test_create_requires_both_route_and_semantic_authorization() -> None:
    authorized = gate().authorize_request(
        request("POST", "/v1.45/containers/create", create_body())
    )
    assert authorized.route.operation is Operation.CREATE
    assert authorized.create is not None
    assert authorized.create.profile == "writer"


def test_semantically_invalid_create_never_produces_request_authority() -> None:
    body = create_body().replace(b'"Privileged":false', b'"Privileged":true')
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        gate().authorize_request(request("POST", "/v1.45/containers/create", body))


def test_response_is_bound_to_the_authorized_request_operation() -> None:
    value = gate()
    authorized = value.authorize_request(
        request("GET", f"/v1.45/containers/{CONTAINER}/json")
    )
    accepted = value.authorize_response(authorized, response(200, b'{"Id":"a"}'))
    assert accepted.status == 200 and accepted.body == b'{"Id":"a"}'
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        value.authorize_response(authorized, response(201, b'{"Id":"a"}'))


def test_neutral_inspect_absence_remains_detail_free() -> None:
    value = gate()
    authorized = value.authorize_request(
        request("GET", f"/v1.45/containers/{CONTAINER}/json")
    )
    assert value.authorize_response(authorized, response(404)).body == b""


def test_request_authority_cannot_cross_gate_instances() -> None:
    first, second = gate(), gate()
    authorized = first.authorize_request(
        request("GET", f"/v1.45/containers/{CONTAINER}/json")
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        second.authorize_response(authorized, response(404))


def test_caller_forged_route_is_not_response_authority() -> None:
    value = gate()
    forged = AuthorizedManifestHandoffSupervisorEngineApiRequest(
        AuthorizedManifestHandoffSupervisorEngineApiRoute(
            Operation.CREATE, request_bytes=2
        ), None, object(),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        value.authorize_response(forged, response(201, b"{}"))


@pytest.mark.parametrize("raw", (
    request("DELETE", f"/v1.45/containers/{CONTAINER}"),
    request("GET", "/v1.45/images/json"),
    request("POST", f"/v1.45/containers/{CONTAINER}/start", b"{}"),
))
def test_framed_but_unapproved_routes_fail_closed(raw) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        gate().authorize_request(raw)


def test_gate_is_inert_and_has_no_transport_surface() -> None:
    value = gate()
    assert repr(value) == "ClosedManifestHandoffSupervisorEngineApiGate()"
    for name in ("listen", "bind", "connect", "recv", "send", "forward", "close"):
        assert not hasattr(value, name)
