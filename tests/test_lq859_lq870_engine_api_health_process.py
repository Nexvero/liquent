from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_composition import compose_manifest_handoff_supervisor_engine_api_health
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority import ManifestHandoffSupervisorEngineApiHealthSocketAuthority
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_listener import ControlledManifestHandoffSupervisorEngineApiHealthListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_process_run import OwnedManifestHandoffSupervisorEngineApiHealthProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_process_status import ManifestHandoffSupervisorEngineApiHealthPhase, ManifestHandoffSupervisorEngineApiHealthStatus
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_serve_loop import BoundedManifestHandoffSupervisorEngineApiHealthServeLoop, ManifestHandoffSupervisorEngineApiHealthServeResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_transport_composition import compose_manifest_handoff_supervisor_engine_api_health_transport
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import ManifestHandoffSupervisorEngineApiProcessBundle


def authority():
    return ManifestHandoffSupervisorEngineApiHealthSocketAuthority(
        Path("/run/liquent/health.sock"), 100, 101, 100, 101, 102, 103, 5, 8
    )


def health_bundle():
    process = object.__new__(ManifestHandoffSupervisorEngineApiProcessBundle)
    return compose_manifest_handoff_supervisor_engine_api_health(process, authority())


def test_inert_transport_composition_binds_one_graph():
    bundle = compose_manifest_handoff_supervisor_engine_api_health_transport(
        health_bundle(), maximum_exchanges=9,
    )
    assert bundle.accept._exchange is bundle.exchange
    assert bundle.serve_loop._accept is bundle.accept
    assert bundle.process_run._listener is bundle.listener
    assert bundle.process_run._loop is bundle.serve_loop
    assert bundle.process_run._status is bundle.status
    assert bundle.status.snapshot().phase is ManifestHandoffSupervisorEngineApiHealthPhase.INITIAL


def test_composition_rejects_foreign_graph_or_bound():
    for graph, maximum in ((object(), 1), (health_bundle(), 0), (health_bundle(), True)):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            compose_manifest_handoff_supervisor_engine_api_health_transport(
                graph, maximum_exchanges=maximum
            )


def process():
    return compose_manifest_handoff_supervisor_engine_api_health_transport(
        health_bundle(), maximum_exchanges=3,
    ).process_run


def test_process_owns_open_run_close_and_status(monkeypatch):
    events, listener = [], object()
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiHealthListener,
                        "open", lambda self: events.append("open") or listener)
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiHealthServeLoop,
                        "run", lambda self, current, stop: events.append(("run", current)) or ManifestHandoffSupervisorEngineApiHealthServeResult(1, "stopped"))
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiHealthListener,
                        "close", lambda self, current: events.append(("close", current)))
    value = process()
    assert value.run(lambda: True).exchanges == 1
    assert events == ["open", ("run", listener), ("close", listener)]
    assert value._status.snapshot().phase is ManifestHandoffSupervisorEngineApiHealthPhase.STOPPED


@pytest.mark.parametrize("stage", ("open", "run", "close"))
def test_process_failure_is_terminal_detail_free_and_closes_when_owned(monkeypatch, stage):
    listener, closes = object(), []
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiHealthListener,
                        "open", lambda self: (_ for _ in ()).throw(RuntimeError("secret")) if stage == "open" else listener)
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiHealthServeLoop,
                        "run", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")) if stage == "run" else ManifestHandoffSupervisorEngineApiHealthServeResult(0, "stopped"))
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiHealthListener,
                        "close", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")) if stage == "close" else closes.append(listener))
    value = process()
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        value.run(lambda: True)
    assert value._status.snapshot().phase is ManifestHandoffSupervisorEngineApiHealthPhase.FAILED
    assert closes == ([listener] if stage == "run" else [])
    assert "secret" not in str(caught.value)


def test_status_is_monotonic_and_fail_closed():
    value = ManifestHandoffSupervisorEngineApiHealthStatus()
    value.move(ManifestHandoffSupervisorEngineApiHealthPhase.INITIAL, ManifestHandoffSupervisorEngineApiHealthPhase.STARTING)
    value.move(ManifestHandoffSupervisorEngineApiHealthPhase.STARTING, ManifestHandoffSupervisorEngineApiHealthPhase.SERVING)
    assert value.snapshot().ready
    value.fail()
    assert value.snapshot().terminal and not value.snapshot().live
    with pytest.raises(ManifestHandoffRegistryUnavailable): value.fail()
