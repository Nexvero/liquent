import threading

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_entrypoint_bundle import ManifestHandoffSupervisorEngineApiHealthEntrypointBundle, compose_manifest_handoff_supervisor_engine_api_health_entrypoint
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_entrypoint_owner import ManifestHandoffSupervisorEngineApiHealthEntrypointOwner
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_process_run import OwnedManifestHandoffSupervisorEngineApiHealthProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_serve_loop import ManifestHandoffSupervisorEngineApiHealthServeResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_signal_run import SignalOwnedManifestHandoffSupervisorEngineApiHealthRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_transport_composition import ManifestHandoffSupervisorEngineApiHealthTransportBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import OwnedManifestHandoffSupervisorEngineApiSignalStopSource


def transport():
    value = object.__new__(ManifestHandoffSupervisorEngineApiHealthTransportBundle)
    object.__setattr__(value, "process_run", object.__new__(
        OwnedManifestHandoffSupervisorEngineApiHealthProcessRun
    ))
    object.__setattr__(value, "serve_loop", type("Loop", (), {"_maximum": 3})())
    return value


def signal_run():
    return SignalOwnedManifestHandoffSupervisorEngineApiHealthRun(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource(),
        object.__new__(OwnedManifestHandoffSupervisorEngineApiHealthProcessRun),
    )


def test_signal_install_run_restore_exact_order(monkeypatch):
    events = []
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "install", lambda self: events.append("install"))
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiHealthProcessRun, "run", lambda self, stop: events.append(("run", stop.__self__)) or ManifestHandoffSupervisorEngineApiHealthServeResult(1, "stopped"))
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "restore", lambda self: events.append("restore"))
    value = signal_run()
    assert value.run().exchanges == 1
    assert events == ["install", ("run", value._signals), "restore"]


@pytest.mark.parametrize("stage", ("install", "run", "restore"))
def test_signal_failure_is_detail_free_and_restores_when_installed(monkeypatch, stage):
    events = []
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "install", lambda self: (_ for _ in ()).throw(RuntimeError("secret")) if stage == "install" else events.append("install"))
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiHealthProcessRun, "run", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")) if stage == "run" else ManifestHandoffSupervisorEngineApiHealthServeResult(0, "stopped"))
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "restore", lambda self: (_ for _ in ()).throw(RuntimeError("secret")) if stage == "restore" else events.append("restore"))
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught: signal_run().run()
    assert events == ([] if stage == "install" else (["install"] if stage == "restore" else ["install", "restore"]))
    assert "secret" not in str(caught.value)


def test_entrypoint_composition_is_inert_and_identity_bound():
    current = transport()
    bundle = compose_manifest_handoff_supervisor_engine_api_health_entrypoint(current)
    assert bundle.transport is current
    assert bundle.process_run._signals is bundle.signals
    assert bundle.process_run._process is current.process_run


def test_entrypoint_rejects_foreign_transport():
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        compose_manifest_handoff_supervisor_engine_api_health_entrypoint(object())


def test_owner_claims_once_and_validates_result(monkeypatch):
    bundle = compose_manifest_handoff_supervisor_engine_api_health_entrypoint(transport())
    monkeypatch.setattr(SignalOwnedManifestHandoffSupervisorEngineApiHealthRun, "run", lambda self: ManifestHandoffSupervisorEngineApiHealthServeResult(3, "exchange_limit"))
    owner = ManifestHandoffSupervisorEngineApiHealthEntrypointOwner(bundle)
    assert owner.run().exchanges == 3
    with pytest.raises(ManifestHandoffRegistryUnavailable): owner.run()


def test_owner_concurrent_claim_has_one_winner(monkeypatch):
    bundle = compose_manifest_handoff_supervisor_engine_api_health_entrypoint(transport())
    entered, release, outcomes = threading.Event(), threading.Event(), []
    def run(self):
        entered.set(); release.wait(2)
        return ManifestHandoffSupervisorEngineApiHealthServeResult(0, "stopped")
    monkeypatch.setattr(SignalOwnedManifestHandoffSupervisorEngineApiHealthRun, "run", run)
    owner = ManifestHandoffSupervisorEngineApiHealthEntrypointOwner(bundle)
    def invoke():
        try: owner.run(); outcomes.append("run")
        except ManifestHandoffRegistryUnavailable: outcomes.append("rejected")
    first = threading.Thread(target=invoke); first.start(); assert entered.wait(1)
    second = threading.Thread(target=invoke); second.start(); second.join(); release.set(); first.join()
    assert sorted(outcomes) == ["rejected", "run"]
