import json
from pathlib import Path

import pytest

from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffSupervisorHandleId,
)
from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffRegistryScopeId,
    ManifestHandoffScopeBinding,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    CreateManifestHandoffSupervisorContainer,
    ManifestHandoffSupervisorEngineConflict,
    ManifestHandoffSupervisorEngineProfile,
    ManifestHandoffSupervisorEngineState,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorImageDigest,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.local_docker_engine_http_client import (
    LocalDockerEngineHttpClient,
)
from liquent_platform.transport.manifest_handoff_supervisor_docker_engine import (
    LocalDockerManifestHandoffSupervisorEngine,
)


CONTAINER = "a" * 64
DIGEST = "sha256:" + "b" * 64
LABELS = {
    "liquent.supervisor.creation": "creation-591",
    "liquent.supervisor.handle": "handle-591",
    "liquent.supervisor.control": "directory-591",
    "liquent.supervisor.launch-document": "launch-591",
    "liquent.supervisor.launch-sha256": "e" * 64,
    "liquent.supervisor.profile": "writer",
}


def entrypoint(labels=LABELS, image=DIGEST):
    return [
        "/opt/liquent/writer-wrapper",
        "--liquent-launch-document", labels["liquent.supervisor.launch-document"],
        "--liquent-launch-sha256", labels["liquent.supervisor.launch-sha256"],
        "--liquent-creation", labels["liquent.supervisor.creation"],
        "--liquent-handle", labels["liquent.supervisor.handle"],
        "--liquent-control-directory", labels["liquent.supervisor.control"],
        "--liquent-image-digest", image,
        "--liquent-profile", labels["liquent.supervisor.profile"],
    ]


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = 0

    def request(self, method, path, body, *, maximum):
        self.calls.append((method, path, body, maximum))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        status, value = response
        if isinstance(value, (dict, list)):
            value = json.dumps(value, separators=(",", ":")).encode()
        return status, value

    def close(self):
        self.closed += 1


def observation(state="created", labels=LABELS, binds=None):
    if binds is None:
        binds = []
    return {
        "Id": CONTAINER,
        "Config": {"Image": DIGEST, "Labels": labels,
                   "Entrypoint": entrypoint(labels)},
        "State": {"Status": state},
        "HostConfig": {
            "Binds": binds,
            "NetworkMode": "none",
            "RestartPolicy": {"Name": "no"},
            "AutoRemove": False,
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "Privileged": False,
            "PidMode": "private",
        },
    }


def client(tmp_path: Path, transport: FakeTransport):
    control = tmp_path / "control"
    control.mkdir(mode=0o700, exist_ok=True)
    (control / "control-artifacts").mkdir(mode=0o700, exist_ok=True)
    launch = control / "launch-binding.json"
    if not launch.exists():
        launch.write_bytes(b"launch")
        launch.chmod(0o600)
    (tmp_path / "source").mkdir(exist_ok=True)
    (tmp_path / "target").mkdir(exist_ok=True)
    return LocalDockerEngineHttpClient(
        Path("/private/run/docker.sock"),
        control_directory_resolver=lambda value: control if value.value == "directory-591" else None,
        writer_command=("/opt/liquent/writer-wrapper",),
        recovery_command=("/opt/liquent/recovery-wrapper",),
        user="65532:65532",
        transport_factory=lambda path, timeout: transport,
    )


def binds(tmp_path):
    control = tmp_path / "control"
    return [
        f"{control / 'control-artifacts'}:/run/liquent/control:rw",
        f"{control / 'launch-binding.json'}:/run/liquent/launch/launch-binding.json:ro",
        f"{tmp_path / 'source'}:/run/liquent/source:ro",
        f"{tmp_path / 'target'}:/run/liquent/target:rw",
    ]


def binding(tmp_path):
    return ManifestHandoffScopeBinding(
        ManifestHandoffRegistryScopeId("scope-591"),
        tmp_path / "source", tmp_path / "target",
    )


def specification(tmp_path):
    return {
        "image": DIGEST,
        "labels": LABELS,
        "profile": "writer",
        "network_mode": "none",
        "restart_policy": "no",
        "auto_remove": False,
        "readonly_rootfs": True,
        "cap_drop": ("ALL",),
        "privileged": False,
        "pid_mode": "private",
        "source_root": tmp_path / "source",
        "target_root": tmp_path / "target",
    }


def test_constructor_is_inert_and_close_is_idempotent(tmp_path):
    transport = FakeTransport([])
    value = client(tmp_path, transport)
    assert transport.calls == []
    assert repr(value) == "LocalDockerEngineHttpClient()"
    value.close()
    value.close()
    assert transport.closed == 1
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        value.inspect(CONTAINER)


def test_create_materializes_fixed_profile_then_inspects(tmp_path):
    transport = FakeTransport([(201, {"Id": CONTAINER, "Warnings": []}),
                               (200, observation(binds=binds(tmp_path)))])
    result = client(tmp_path, transport).create(specification(tmp_path))
    method, path, body, maximum = transport.calls[0]
    payload = json.loads(body)
    assert (method, path, maximum) == ("POST", "/v1.45/containers/create", 1_048_576)
    assert payload["Entrypoint"] == entrypoint()
    assert payload["User"] == "65532:65532"
    assert payload["HostConfig"] == {
        "AutoRemove": False,
        "Binds": binds(tmp_path),
        "CapDrop": ["ALL"],
        "NetworkMode": "none",
        "PidMode": "private",
        "Privileged": False,
        "ReadonlyRootfs": True,
        "RestartPolicy": {"MaximumRetryCount": 0, "Name": "no"},
    }
    assert result["id"] == CONTAINER and result["state"] == "created"


def test_find_uses_exact_canonical_filter_and_bounded_inspection(tmp_path):
    transport = FakeTransport([([200][0], [{"Id": CONTAINER}]),
                               (200, observation(binds=binds(tmp_path)))])
    result = client(tmp_path, transport).find({"liquent.supervisor.creation": "creation-591"})
    assert result[0]["labels"] == LABELS
    assert transport.calls[0][0] == "GET"
    assert transport.calls[0][1].startswith("/v1.45/containers/json?all=1&filters=")


def test_inspect_not_found_is_neutral_but_other_status_is_unavailable(tmp_path):
    assert client(tmp_path, FakeTransport([(404, b"")])).inspect(CONTAINER) is None
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        client(tmp_path, FakeTransport([(500, b"daemon detail")])).inspect(CONTAINER)


def test_start_wait_stop_and_kill_have_fixed_paths(tmp_path):
    transport = FakeTransport([
        (204, b""), (200, {"StatusCode": 0}),
        (200, observation("exited", binds=binds(tmp_path))),
        (304, b""), (204, b""),
    ])
    value = client(tmp_path, transport)
    value.start(CONTAINER)
    assert value.wait(CONTAINER)["state"] == "exited"
    value.stop(CONTAINER)
    value.kill(CONTAINER)
    assert [call[1] for call in transport.calls] == [
        f"/v1.45/containers/{CONTAINER}/start",
        f"/v1.45/containers/{CONTAINER}/wait?condition=not-running",
        f"/v1.45/containers/{CONTAINER}/json",
        f"/v1.45/containers/{CONTAINER}/stop?t=10",
        f"/v1.45/containers/{CONTAINER}/kill?signal=KILL",
    ]


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(network_mode="bridge"),
    lambda value: value.update(privileged=True),
    lambda value: value["labels"].update(extra="caller"),
    lambda value: value.update(profile="recovery"),
])
def test_create_rejects_profile_or_security_override_without_io(tmp_path, mutation):
    transport = FakeTransport([])
    value = specification(tmp_path)
    value["labels"] = dict(value["labels"])
    mutation(value)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        client(tmp_path, transport).create(value)
    assert transport.calls == []


def test_transport_and_decode_failures_are_detail_free(tmp_path):
    for response in (RuntimeError("secret"), (200, b'{"a":1,"a":2}')):
        with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
            client(tmp_path, FakeTransport([response])).inspect(CONTAINER)
        assert str(caught.value) == "manifest_handoff_registry_unavailable"
        assert "secret" not in str(caught.value)


def test_existing_engine_accepts_client_create_result(tmp_path):
    transport = FakeTransport([(200, []), (201, {"Id": CONTAINER}),
                               (200, observation(binds=binds(tmp_path)))])
    docker = client(tmp_path, transport)
    engine = LocalDockerManifestHandoffSupervisorEngine(
        docker,
        writer_image=ManifestHandoffSupervisorImageDigest(DIGEST),
        recovery_image=ManifestHandoffSupervisorImageDigest("sha256:" + "c" * 64),
    )
    created = engine.create(CreateManifestHandoffSupervisorContainer(
        ManifestHandoffSupervisorHandleId("handle-591"),
        ManifestHandoffSupervisorCreationId("creation-591"),
        ManifestHandoffSupervisorControlDirectoryId("directory-591"),
        ManifestHandoffSupervisorImageDigest(DIGEST),
        ManifestHandoffSupervisorControlArtifactId("launch-591"),
        ManifestHandoffSupervisorLaunchDocumentDigest("e" * 64),
        ManifestHandoffSupervisorEngineProfile.WRITER,
        binding(tmp_path),
    ))
    assert created.runtime_container_id.value == CONTAINER
    assert created.launch_document_id.value == "launch-591"
    assert created.launch_document_digest.value == "e" * 64
    assert len(transport.calls) == 3


def test_engine_retry_adopts_only_the_exact_launch_anchor(tmp_path):
    transport = FakeTransport([(200, [{"Id": CONTAINER}]),
                               (200, observation(binds=binds(tmp_path)))])
    engine = LocalDockerManifestHandoffSupervisorEngine(
        client(tmp_path, transport),
        writer_image=ManifestHandoffSupervisorImageDigest(DIGEST),
        recovery_image=ManifestHandoffSupervisorImageDigest("sha256:" + "c" * 64),
    )
    created = engine.create(CreateManifestHandoffSupervisorContainer(
        ManifestHandoffSupervisorHandleId("handle-591"),
        ManifestHandoffSupervisorCreationId("creation-591"),
        ManifestHandoffSupervisorControlDirectoryId("directory-591"),
        ManifestHandoffSupervisorImageDigest(DIGEST),
        ManifestHandoffSupervisorControlArtifactId("launch-591"),
        ManifestHandoffSupervisorLaunchDocumentDigest("e" * 64),
        ManifestHandoffSupervisorEngineProfile.WRITER,
        binding(tmp_path),
    ))
    assert created.runtime_container_id.value == CONTAINER
    assert len(transport.calls) == 2


@pytest.mark.parametrize("key,value", [
    ("liquent.supervisor.launch-document", "another-launch"),
    ("liquent.supervisor.launch-sha256", "f" * 64),
])
def test_engine_retry_rejects_divergent_launch_anchor_without_create(tmp_path, key, value):
    labels = dict(LABELS)
    labels[key] = value
    transport = FakeTransport([
        (200, [{"Id": CONTAINER}]),
        (200, observation(labels=labels, binds=binds(tmp_path))),
    ])
    engine = LocalDockerManifestHandoffSupervisorEngine(
        client(tmp_path, transport),
        writer_image=ManifestHandoffSupervisorImageDigest(DIGEST),
        recovery_image=ManifestHandoffSupervisorImageDigest("sha256:" + "c" * 64),
    )
    result = engine.create(CreateManifestHandoffSupervisorContainer(
        ManifestHandoffSupervisorHandleId("handle-591"),
        ManifestHandoffSupervisorCreationId("creation-591"),
        ManifestHandoffSupervisorControlDirectoryId("directory-591"),
        ManifestHandoffSupervisorImageDigest(DIGEST),
        ManifestHandoffSupervisorControlArtifactId("launch-591"),
        ManifestHandoffSupervisorLaunchDocumentDigest("e" * 64),
        ManifestHandoffSupervisorEngineProfile.WRITER,
        binding(tmp_path),
    ))
    assert type(result) is ManifestHandoffSupervisorEngineConflict
    assert len(transport.calls) == 2


@pytest.mark.parametrize("value", ["E" * 64, "e" * 63, "g" * 64, "sha256:" + "e" * 64])
def test_launch_document_digest_is_exact_lowercase_sha256(value):
    with pytest.raises(ValueError):
        ManifestHandoffSupervisorLaunchDocumentDigest(value)


def test_integrated_wait_preserves_terminal_state(tmp_path):
    transport = FakeTransport([(200, {"StatusCode": 0}),
                               (200, observation("dead", binds=binds(tmp_path)))])
    docker = client(tmp_path, transport)
    result = docker.wait(CONTAINER)
    assert result["state"] == ManifestHandoffSupervisorEngineState.DEAD.value
