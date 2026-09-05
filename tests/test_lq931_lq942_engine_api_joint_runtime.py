from pathlib import Path

import pytest

from liquent_platform.application.health import Readiness
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import ManifestHandoffSupervisorEngineApiProcessBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_composition import ManifestHandoffSupervisorEngineApiHealthBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_process_run import OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_runtime_composition import ManifestHandoffSupervisorEngineApiHealthPollRuntimeBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_host_preflight import ManifestHandoffSupervisorEngineApiHostPreflight
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_joint_owner import JointManifestHandoffSupervisorEngineApiProcessOwner
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_listener import BoundedManifestHandoffSupervisorEngineApiPollListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_loop import StopAwareManifestHandoffSupervisorEngineApiPollLoop
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_process_run import OwnedManifestHandoffSupervisorEngineApiPollProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_runtime_composition import ManifestHandoffSupervisorEngineApiPollRuntimeBundle, compose_manifest_handoff_supervisor_engine_api_poll_runtime
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import ManifestHandoffSupervisorEngineApiProcessPhase, ManifestHandoffSupervisorEngineApiProcessStatus
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import ManifestHandoffSupervisorEngineApiServeResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import ManifestHandoffSupervisorEngineApiProxySettings
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import OwnedManifestHandoffSupervisorEngineApiSignalStopSource


def settings():
    return ManifestHandoffSupervisorEngineApiProxySettings.from_mapping({
        "proxy_socket":"/run/liquent/engine.sock","daemon_socket":"/var/run/docker.sock","control_root":"/srv/liquent/control","source_root":"/srv/liquent/source","target_root":"/srv/liquent/target","writer_command":"/opt/writer","recovery_command":"/opt/recovery","proxy_uid":"100","client_gid":"101","daemon_uid":"0","daemon_gid":"998","host_owner_uid":"102","host_owner_gid":"103","data_owner_uid":"104","data_gid":"105","wrapper_uid":"106","wrapper_gid":"107","client_timeout_seconds":"5","daemon_timeout_seconds":"5","listener_backlog":"8","maximum_exchanges":"9"
    })


def test_poll_proxy_composition_reuses_observed_status_and_graph():
    bundle = compose_manifest_handoff_supervisor_engine_api_poll_runtime(settings(), poll_timeout_seconds=.25)
    assert bundle.process_run._status is bundle.observed_bundle.status
    assert bundle.listener._listener is bundle.observed_bundle.process_run._process._listener
    assert bundle.serve_loop._accept is bundle.observed_bundle.process_run._process._loop._accept
    assert bundle.serve_loop._maximum == 9


def test_poll_process_runs_preflight_open_loop_close(monkeypatch):
    preflight = object.__new__(ManifestHandoffSupervisorEngineApiHostPreflight)
    listener = object.__new__(BoundedManifestHandoffSupervisorEngineApiPollListener)
    loop = object.__new__(StopAwareManifestHandoffSupervisorEngineApiPollLoop)
    status, events, active = ManifestHandoffSupervisorEngineApiProcessStatus(), [], object()
    monkeypatch.setattr(ManifestHandoffSupervisorEngineApiHostPreflight, "check_before_listener", lambda self: events.append("before") or Readiness(True, "ready"))
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiPollListener, "open", lambda self: events.append("open") or active)
    monkeypatch.setattr(ManifestHandoffSupervisorEngineApiHostPreflight, "check", lambda self: events.append("full") or Readiness(True, "ready"))
    monkeypatch.setattr(StopAwareManifestHandoffSupervisorEngineApiPollLoop, "run", lambda self, current, stop: events.append(("run", current)) or ManifestHandoffSupervisorEngineApiServeResult(0, "stopped"))
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiPollListener, "close", lambda self, current: events.append(("close", current)))
    result = OwnedManifestHandoffSupervisorEngineApiPollProcessRun(preflight, listener, loop, status).run(lambda: True)
    assert result.reason == "stopped"
    assert events == ["before", "open", "full", ("run", active), ("close", active)]
    assert status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.STOPPED


def joint_bundles():
    observed = object.__new__(ManifestHandoffSupervisorEngineApiProcessBundle)
    proxy = object.__new__(ManifestHandoffSupervisorEngineApiPollRuntimeBundle)
    object.__setattr__(proxy, "observed_bundle", observed)
    object.__setattr__(proxy, "process_run", object.__new__(OwnedManifestHandoffSupervisorEngineApiPollProcessRun))
    health_graph = object.__new__(ManifestHandoffSupervisorEngineApiHealthBundle)
    object.__setattr__(health_graph, "process_bundle", observed)
    health = object.__new__(ManifestHandoffSupervisorEngineApiHealthPollRuntimeBundle)
    object.__setattr__(health, "health", health_graph)
    object.__setattr__(health, "process_run", object.__new__(OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun))
    return proxy, health


def test_joint_owner_runs_both_with_one_signal_lifecycle(monkeypatch):
    events = []
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "install", lambda self: events.append("install"))
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "restore", lambda self: events.append("restore"))
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiPollProcessRun, "run", lambda self, stop: events.append("proxy") or ManifestHandoffSupervisorEngineApiServeResult(1, "stopped"))
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun, "run", lambda self, stop: events.append("health") or ManifestHandoffSupervisorEngineApiServeResult(0, "stopped"))
    owner = JointManifestHandoffSupervisorEngineApiProcessOwner(*joint_bundles(), join_timeout_seconds=1)
    proxy, health = owner.run()
    assert (proxy.exchanges, health.exchanges) == (1, 0)
    assert events[0] == "install" and events[-1] == "restore"
    assert sorted(events[1:-1]) == ["health", "proxy"]
    with pytest.raises(ManifestHandoffRegistryUnavailable): owner.run()


@pytest.mark.parametrize("failed", ("proxy", "health"))
def test_joint_failure_stops_peer_and_is_detail_free(monkeypatch, failed):
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "install", lambda self: None)
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "restore", lambda self: None)
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiPollProcessRun, "run", lambda self, stop: (_ for _ in ()).throw(RuntimeError("secret")) if failed == "proxy" else ManifestHandoffSupervisorEngineApiServeResult(0, "stopped"))
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun, "run", lambda self, stop: (_ for _ in ()).throw(RuntimeError("secret")) if failed == "health" else ManifestHandoffSupervisorEngineApiServeResult(0, "stopped"))
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        JointManifestHandoffSupervisorEngineApiProcessOwner(*joint_bundles(), join_timeout_seconds=1).run()
    assert "secret" not in str(caught.value)


def test_joint_owner_rejects_mismatched_observed_bundle():
    proxy, health = joint_bundles()
    object.__setattr__(health.health, "process_bundle", object.__new__(ManifestHandoffSupervisorEngineApiProcessBundle))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        JointManifestHandoffSupervisorEngineApiProcessOwner(proxy, health, join_timeout_seconds=1)
