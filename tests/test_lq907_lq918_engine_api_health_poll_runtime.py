from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import ManifestHandoffSupervisorEngineApiProcessBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority import ManifestHandoffSupervisorEngineApiHealthSocketAuthority
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_listener import BoundedManifestHandoffSupervisorEngineApiHealthPollListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_loop import StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_process_run import OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_runtime_composition import compose_manifest_handoff_supervisor_engine_api_health_poll_runtime
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_process_status import ManifestHandoffSupervisorEngineApiHealthPhase, ManifestHandoffSupervisorEngineApiHealthStatus
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_run_settings import ManifestHandoffSupervisorEngineApiHealthRunSettings
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_serve_loop import ManifestHandoffSupervisorEngineApiHealthServeResult


def dependencies():
    listener = object.__new__(BoundedManifestHandoffSupervisorEngineApiHealthPollListener)
    loop = object.__new__(StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop)
    return listener, loop, ManifestHandoffSupervisorEngineApiHealthStatus()


def test_poll_process_open_run_close_and_status(monkeypatch):
    events, active = [], object()
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiHealthPollListener, "open", lambda self: events.append("open") or active)
    monkeypatch.setattr(StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop, "run", lambda self, current, stop: events.append(("run", current)) or ManifestHandoffSupervisorEngineApiHealthServeResult(0, "stopped"))
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiHealthPollListener, "close", lambda self, current: events.append(("close", current)))
    value = OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun(*dependencies())
    assert value.run(lambda: True).reason == "stopped"
    assert events == ["open", ("run", active), ("close", active)]
    assert value._status.snapshot().phase is ManifestHandoffSupervisorEngineApiHealthPhase.STOPPED


@pytest.mark.parametrize("stage", ("open", "run", "close"))
def test_poll_process_failures_are_terminal_and_detail_free(monkeypatch, stage):
    active = object()
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiHealthPollListener, "open", lambda self: (_ for _ in ()).throw(RuntimeError("secret")) if stage == "open" else active)
    monkeypatch.setattr(StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop, "run", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")) if stage == "run" else ManifestHandoffSupervisorEngineApiHealthServeResult(0, "stopped"))
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiHealthPollListener, "close", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")) if stage == "close" else None)
    value = OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun(*dependencies())
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught: value.run(lambda: False)
    assert value._status.snapshot().phase is ManifestHandoffSupervisorEngineApiHealthPhase.FAILED
    assert "secret" not in str(caught.value)


def test_poll_runtime_retains_observed_process_and_poll_bound():
    process = object.__new__(ManifestHandoffSupervisorEngineApiProcessBundle)
    authority = ManifestHandoffSupervisorEngineApiHealthSocketAuthority(
        Path("/run/liquent/health.sock"), 100, 101, 100, 101, 102, 103, 5, 8
    )
    bundle = compose_manifest_handoff_supervisor_engine_api_health_poll_runtime(
        process, authority, ManifestHandoffSupervisorEngineApiHealthRunSettings(7),
        poll_timeout_seconds=.25,
    )
    assert bundle.health.process_bundle is process
    assert bundle.health.owner._bundle is process
    assert bundle.listener._timeout == .25
    assert bundle.serve_loop._accept._poll_timeout == .25
    assert bundle.serve_loop._maximum == 7
    assert bundle.process_run._status is bundle.status


@pytest.mark.parametrize("timeout", (0, -1, True, 61))
def test_poll_runtime_rejects_invalid_poll_timeout(timeout):
    process = object.__new__(ManifestHandoffSupervisorEngineApiProcessBundle)
    authority = ManifestHandoffSupervisorEngineApiHealthSocketAuthority(
        Path("/run/liquent/health.sock"), 100, 101, 100, 101, 102, 103, 5, 8
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        compose_manifest_handoff_supervisor_engine_api_health_poll_runtime(
            process, authority, ManifestHandoffSupervisorEngineApiHealthRunSettings(1),
            poll_timeout_seconds=timeout,
        )
