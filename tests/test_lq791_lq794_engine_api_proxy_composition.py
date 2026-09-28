from pathlib import Path

import pytest

import liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition as composition
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import (
    ManifestHandoffSupervisorEngineApiProxySettings,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_signal_run import (
    SignalOwnedManifestHandoffSupervisorEngineApiRun,
)


def settings() -> ManifestHandoffSupervisorEngineApiProxySettings:
    return ManifestHandoffSupervisorEngineApiProxySettings.from_mapping({
        "proxy_socket": "/run/liquent/engine.sock",
        "daemon_socket": "/var/run/docker.sock",
        "control_root": "/srv/liquent/control",
        "source_root": "/srv/liquent/source",
        "target_root": "/srv/liquent/target",
        "writer_command": "/opt/liquent/writer-wrapper",
        "recovery_command": "/opt/liquent/recovery-wrapper",
        "proxy_uid": "10001", "client_gid": "10002",
        "daemon_uid": "0", "daemon_gid": "998",
        "host_owner_uid": "10003", "host_owner_gid": "10004",
        "data_owner_uid": "10005", "data_gid": "10006",
        "wrapper_uid": "10007", "wrapper_gid": "10008",
        "client_timeout_seconds": "15", "daemon_timeout_seconds": "30",
        "listener_backlog": "16", "maximum_exchanges": "10000",
    })


def test_one_settings_value_composes_the_complete_inert_graph() -> None:
    result = composition.compose_manifest_handoff_supervisor_engine_api_proxy(settings())
    assert type(result) is SignalOwnedManifestHandoffSupervisorEngineApiRun
    process = result._process
    loop = process._loop
    accept = loop._accept
    connected = accept._exchange
    verified = connected._exchange
    assert verified._exchange._gate._create._user == "10007:10008"
    assert verified._client._uid == 10003
    assert verified._client._gid == 10002
    assert verified._daemon._uid == 0
    assert verified._daemon._gid == 998
    assert connected._connector._socket == Path("/var/run/docker.sock")
    assert connected._connector._timeout == 30.0
    assert accept._timeout == 15.0
    assert loop._maximum == 10_000
    assert process._listener._backlog == 16


def test_shared_paths_and_identity_facts_are_bound_consistently() -> None:
    result = composition.compose_manifest_handoff_supervisor_engine_api_proxy(settings())
    process = result._process
    accept = process._loop._accept
    verified = accept._exchange._exchange
    assert process._listener._path is process._preflight._proxy_socket
    assert accept._path is process._preflight._proxy_socket
    assert verified._client._socket is process._preflight._proxy_socket
    assert verified._daemon._socket is process._preflight._daemon_socket
    assert accept._exchange._connector._socket is process._preflight._daemon_socket
    assert process._listener._uid == process._preflight._proxy_uid
    assert process._listener._parent_uid == process._preflight._host_uid


@pytest.mark.parametrize("value", (None, object(), {}, "settings"))
def test_only_the_exact_closed_settings_type_is_accepted(value) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        composition.compose_manifest_handoff_supervisor_engine_api_proxy(value)


def test_constructor_failure_is_detail_free(monkeypatch) -> None:
    class Broken:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("private composition detail")

    monkeypatch.setattr(
        composition, "ClosedManifestHandoffSupervisorEngineApiGate", Broken
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        composition.compose_manifest_handoff_supervisor_engine_api_proxy(settings())
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "private composition detail" not in str(caught.value)


def test_composition_performs_no_host_or_environment_io(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("I/O during composition")

    for name in ("open", "lstat", "fstat", "getenv"):
        monkeypatch.setattr(composition, name, forbidden, raising=False)
    result = composition.compose_manifest_handoff_supervisor_engine_api_proxy(settings())
    assert repr(result) == "SignalOwnedManifestHandoffSupervisorEngineApiRun()"


def test_source_has_no_environment_entrypoint_or_readiness_claim() -> None:
    source = Path(composition.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "os.environ", "getenv(", "PlatformSettings", "create_app",
        "production_ready", "compose.yaml", ".run(",
    ):
        assert forbidden not in source
