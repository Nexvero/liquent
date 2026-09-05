from pathlib import Path

import pytest

from liquent_platform.application.health import Readiness
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_host_preflight import ManifestHandoffSupervisorEngineApiHostPreflight
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener import ControlledManifestHandoffSupervisorEngineApiListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_run import OwnedManifestHandoffSupervisorEngineApiProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import BoundedManifestHandoffSupervisorEngineApiServeLoop, ManifestHandoffSupervisorEngineApiServeResult


def dependencies():
    preflight = ManifestHandoffSupervisorEngineApiHostPreflight(
        proxy_socket=Path("/run/liquent/engine.sock"),
        daemon_socket=Path("/var/run/docker.sock"),
        control_root=Path("/srv/liquent/control"),
        source_root=Path("/srv/liquent/source"),
        target_root=Path("/srv/liquent/target"),
        proxy_uid=10001, client_gid=10002, daemon_uid=0, daemon_gid=998,
        host_owner_uid=10001, host_owner_gid=10002,
        data_owner_uid=10003, data_gid=10004,
    )
    listener = ControlledManifestHandoffSupervisorEngineApiListener(
        socket_path=Path("/run/liquent/engine.sock"),
        proxy_uid=10001, client_gid=10002,
        parent_uid=10001, parent_gid=10002, backlog=8,
        socket_factory=lambda family, kind: None,
    )
    serve_loop = object.__new__(BoundedManifestHandoffSupervisorEngineApiServeLoop)
    return preflight, listener, serve_loop


def process():
    return OwnedManifestHandoffSupervisorEngineApiProcessRun(*dependencies())


def test_exact_preactivation_open_full_preflight_run_retire_order(monkeypatch) -> None:
    events, listener = [], object()
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiHostPreflight,
        "check_before_listener",
        lambda self: events.append("dependencies") or Readiness(
            True, "manifest_handoff_supervisor_host_dependencies_ready"
        ),
    )
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiListener,
        "open", lambda self: events.append("open") or listener,
    )
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiHostPreflight,
        "check", lambda self: events.append("full") or Readiness(
            True, "manifest_handoff_supervisor_host_ready"
        ),
    )
    expected = ManifestHandoffSupervisorEngineApiServeResult(2, "stopped")
    monkeypatch.setattr(
        BoundedManifestHandoffSupervisorEngineApiServeLoop,
        "run", lambda self, current, stop: events.append(("run", current)) or expected,
    )
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiListener,
        "close", lambda self, current: events.append(("retire", current)),
    )
    assert process().run(lambda: True) == expected
    assert events == [
        "dependencies", "open", "full", ("run", listener),
        ("retire", listener),
    ]


def test_failed_dependency_preflight_has_no_listener_effect(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiHostPreflight,
        "check_before_listener", lambda self: Readiness(False, "unavailable"),
    )
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiListener,
        "open", lambda self: events.append("open"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        process().run(lambda: False)
    assert events == []


@pytest.mark.parametrize("stage", ("full", "run"))
def test_every_post_open_failure_retires_listener_once(monkeypatch, stage) -> None:
    listener, retires = object(), []
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiHostPreflight,
        "check_before_listener", lambda self: Readiness(
            True, "manifest_handoff_supervisor_host_dependencies_ready"
        ),
    )
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiListener,
        "open", lambda self: listener,
    )
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiHostPreflight,
        "check", lambda self: (
            Readiness(False, "unavailable") if stage == "full"
            else Readiness(True, "manifest_handoff_supervisor_host_ready")
        ),
    )
    monkeypatch.setattr(
        BoundedManifestHandoffSupervisorEngineApiServeLoop,
        "run", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")),
    )
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiListener,
        "close", lambda self, current: retires.append(current),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        process().run(lambda: False)
    assert retires == [listener]
    assert "secret" not in str(caught.value)


def test_open_failure_has_no_retire_target(monkeypatch) -> None:
    retires = []
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiHostPreflight,
        "check_before_listener", lambda self: Readiness(
            True, "manifest_handoff_supervisor_host_dependencies_ready"
        ),
    )
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiListener,
        "open", lambda self: (_ for _ in ()).throw(RuntimeError("secret")),
    )
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiListener,
        "close", lambda *args: retires.append("retire"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        process().run(lambda: False)
    assert retires == []


def test_retire_failure_after_success_is_unavailable(monkeypatch) -> None:
    listener = object()
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiHostPreflight,
        "check_before_listener", lambda self: Readiness(
            True, "manifest_handoff_supervisor_host_dependencies_ready"
        ),
    )
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiListener, "open", lambda self: listener)
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiHostPreflight,
        "check", lambda self: Readiness(True, "manifest_handoff_supervisor_host_ready"),
    )
    monkeypatch.setattr(
        BoundedManifestHandoffSupervisorEngineApiServeLoop,
        "run", lambda *args: ManifestHandoffSupervisorEngineApiServeResult(1, "exchange_limit"),
    )
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiListener,
        "close", lambda *args: (_ for _ in ()).throw(RuntimeError("retire secret")),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        process().run(lambda: False)
    assert "secret" not in str(caught.value)


def test_process_run_has_no_signal_thread_entrypoint_or_close_surface() -> None:
    value = process()
    assert repr(value) == "OwnedManifestHandoffSupervisorEngineApiProcessRun()"
    for name in ("signal", "thread", "main", "entrypoint", "close"):
        assert not hasattr(value, name)
