from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_composition as composition
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import (
    compose_manifest_handoff_supervisor_engine_api_proxy_bundle,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority import (
    ManifestHandoffSupervisorEngineApiHealthSocketAuthority,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_protocol import (
    ClosedManifestHandoffSupervisorEngineApiHealthProtocol,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_owner import (
    ManifestHandoffSupervisorEngineApiProcessOwner,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import (
    ManifestHandoffSupervisorEngineApiProxySettings,
)


def process_bundle():
    settings = ManifestHandoffSupervisorEngineApiProxySettings.from_mapping({
        "proxy_socket": "/run/liquent/engine.sock", "daemon_socket": "/var/run/docker.sock",
        "control_root": "/srv/liquent/control", "source_root": "/srv/liquent/source",
        "target_root": "/srv/liquent/target", "writer_command": "/opt/liquent/writer",
        "recovery_command": "/opt/liquent/recovery", "proxy_uid": "10001",
        "client_gid": "10002", "daemon_uid": "0", "daemon_gid": "998",
        "host_owner_uid": "10003", "host_owner_gid": "10004",
        "data_owner_uid": "10005", "data_gid": "10006", "wrapper_uid": "10007",
        "wrapper_gid": "10008", "client_timeout_seconds": "15",
        "daemon_timeout_seconds": "30", "listener_backlog": "16",
        "maximum_exchanges": "10000",
    })
    return compose_manifest_handoff_supervisor_engine_api_proxy_bundle(settings)


def authority(path="/run/liquent/health.sock"):
    return ManifestHandoffSupervisorEngineApiHealthSocketAuthority.from_mapping({
        "socket_path": path, "socket_uid": "10011", "socket_gid": "10012",
        "parent_uid": "10013", "parent_gid": "10014", "peer_uid": "10015",
        "peer_gid": "10016", "timeout_seconds": "5", "backlog": "8",
    })


def test_complete_health_graph_has_exact_identity_bindings() -> None:
    process, current = process_bundle(), authority()
    result = composition.compose_manifest_handoff_supervisor_engine_api_health(
        process, current
    )
    assert type(result) is composition.ManifestHandoffSupervisorEngineApiHealthBundle
    assert result.process_bundle is process
    assert result.authority is current
    assert type(result.owner) is ManifestHandoffSupervisorEngineApiProcessOwner
    assert type(result.protocol) is ClosedManifestHandoffSupervisorEngineApiHealthProtocol
    assert result.owner._bundle is process
    assert result.protocol._owner is result.owner
    assert result.peer_policy._socket is current.socket_path
    assert result.peer_policy._uid == current.peer_uid
    assert result.peer_policy._gid == current.peer_gid
    assert result.peer_policy._timeout == 5.0


def test_health_bundle_is_frozen_initial_and_detail_free() -> None:
    result = composition.compose_manifest_handoff_supervisor_engine_api_health(
        process_bundle(), authority()
    )
    with pytest.raises(FrozenInstanceError):
        result.authority = authority("/run/liquent/other.sock")
    assert result.owner.snapshot().phase.value == "initial"
    assert result.owner.readiness().ready is False
    assert repr(result) == "ManifestHandoffSupervisorEngineApiHealthBundle()"
    assert "health.sock" not in repr(result)


def test_mixed_components_from_two_graphs_fail_closed() -> None:
    first = composition.compose_manifest_handoff_supervisor_engine_api_health(
        process_bundle(), authority()
    )
    second = composition.compose_manifest_handoff_supervisor_engine_api_health(
        process_bundle(), authority("/run/liquent/second.sock")
    )
    base = (
        first.process_bundle, first.authority, first.owner,
        first.peer_policy, first.protocol,
    )
    for index, replacement in enumerate((
        second.process_bundle, second.authority, second.owner,
        second.peer_policy, second.protocol,
    )):
        values = list(base)
        values[index] = replacement
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            composition.ManifestHandoffSupervisorEngineApiHealthBundle(*values)


@pytest.mark.parametrize("first,second", (
    (None, None), (object(), None), (None, object()),
    ("bundle", "authority"),
))
def test_composer_accepts_only_exact_process_bundle_and_authority(first, second) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        composition.compose_manifest_handoff_supervisor_engine_api_health(first, second)


def test_composition_failure_is_detail_free(monkeypatch) -> None:
    monkeypatch.setattr(
        composition, "ManifestHandoffSupervisorEngineApiProcessOwner",
        lambda value: (_ for _ in ()).throw(RuntimeError("private detail")),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        composition.compose_manifest_handoff_supervisor_engine_api_health(
            process_bundle(), authority()
        )
    assert "private" not in str(caught.value)


def test_composition_has_no_host_environment_listener_or_run_effect(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("effect during health composition")

    for name in ("open", "lstat", "getenv", "listen", "accept", "run"):
        monkeypatch.setattr(composition, name, forbidden, raising=False)
    result = composition.compose_manifest_handoff_supervisor_engine_api_health(
        process_bundle(), authority()
    )
    assert result.owner.snapshot().phase.value == "initial"
