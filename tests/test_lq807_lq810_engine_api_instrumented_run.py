from pathlib import Path

import pytest

from liquent_platform.application.health import Readiness
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import (
    compose_manifest_handoff_supervisor_engine_api_proxy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_host_preflight import (
    ManifestHandoffSupervisorEngineApiHostPreflight,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener import (
    ControlledManifestHandoffSupervisorEngineApiListener,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_run import (
    OwnedManifestHandoffSupervisorEngineApiProcessRun,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import (
    ManifestHandoffSupervisorEngineApiProcessPhase,
    ManifestHandoffSupervisorEngineApiProcessStatus,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import (
    BoundedManifestHandoffSupervisorEngineApiServeLoop,
    ManifestHandoffSupervisorEngineApiServeResult,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import (
    ManifestHandoffSupervisorEngineApiProxySettings,
)


def _objects():
    return (
        object.__new__(ManifestHandoffSupervisorEngineApiHostPreflight),
        object.__new__(ControlledManifestHandoffSupervisorEngineApiListener),
        object.__new__(BoundedManifestHandoffSupervisorEngineApiServeLoop),
    )


def _patch_success(monkeypatch, calls, failure=None):
    listener = object()

    def before(self):
        calls.append("before")
        if failure == "before":
            raise RuntimeError("private before detail")
        return Readiness(True, "manifest_handoff_supervisor_host_dependencies_ready")

    def open_listener(self):
        calls.append("open")
        if failure == "open":
            raise RuntimeError("private open detail")
        return listener

    def current(self):
        calls.append("current")
        if failure == "current":
            raise RuntimeError("private current detail")
        return Readiness(True, "manifest_handoff_supervisor_host_ready")

    def loop(self, current_listener, stop):
        calls.append("loop")
        assert current_listener is listener
        if failure == "loop":
            raise RuntimeError("private loop detail")
        return ManifestHandoffSupervisorEngineApiServeResult(2, "stopped")

    def close(self, current_listener):
        calls.append("close")
        assert current_listener is listener
        if failure == "close":
            raise RuntimeError("private close detail")

    monkeypatch.setattr(ManifestHandoffSupervisorEngineApiHostPreflight, "check_before_listener", before)
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiListener, "open", open_listener)
    monkeypatch.setattr(ManifestHandoffSupervisorEngineApiHostPreflight, "check", current)
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiServeLoop, "run", loop)
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiListener, "close", close)


def test_real_owned_run_reaches_stopped_only_after_listener_retire(monkeypatch) -> None:
    calls = []
    _patch_success(monkeypatch, calls)
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    process = OwnedManifestHandoffSupervisorEngineApiProcessRun(
        *_objects(), status=status
    )
    result = process.run(lambda: False)
    assert result == ManifestHandoffSupervisorEngineApiServeResult(2, "stopped")
    assert calls == ["before", "open", "current", "loop", "close"]
    assert status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.STOPPED


@pytest.mark.parametrize("failure,expected", (
    ("before", ["before"]),
    ("open", ["before", "open"]),
    ("current", ["before", "open", "current", "close"]),
    ("loop", ["before", "open", "current", "loop", "close"]),
    ("close", ["before", "open", "current", "loop", "close"]),
))
def test_every_real_run_failure_becomes_terminal_failed(
    monkeypatch, failure, expected
) -> None:
    calls = []
    _patch_success(monkeypatch, calls, failure)
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    process = OwnedManifestHandoffSupervisorEngineApiProcessRun(
        *_objects(), status=status
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        process.run(lambda: False)
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert calls == expected
    snapshot = status.snapshot()
    assert snapshot.phase is ManifestHandoffSupervisorEngineApiProcessPhase.FAILED
    assert snapshot.ready is False and snapshot.live is False


def test_failed_or_stopped_run_cannot_be_reused(monkeypatch) -> None:
    calls = []
    _patch_success(monkeypatch, calls)
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    process = OwnedManifestHandoffSupervisorEngineApiProcessRun(
        *_objects(), status=status
    )
    process.run(lambda: False)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        process.run(lambda: False)
    assert calls == ["before", "open", "current", "loop", "close"]


def _settings():
    return ManifestHandoffSupervisorEngineApiProxySettings.from_mapping({
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


def test_composition_binds_exactly_one_status_to_the_real_process() -> None:
    graph = compose_manifest_handoff_supervisor_engine_api_proxy(_settings())
    status = graph._process._status
    assert type(status) is ManifestHandoffSupervisorEngineApiProcessStatus
    assert status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.INITIAL


def test_only_exact_status_can_be_injected() -> None:
    before, listener, loop = _objects()
    for value in (object(), "status"):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            OwnedManifestHandoffSupervisorEngineApiProcessRun(
                before, listener, loop, status=value
            )
