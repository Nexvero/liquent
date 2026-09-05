import threading
from pathlib import Path

import pytest

import liquent_platform.transport.manifest_handoff_supervisor_engine_api_entrypoint as entrypoint
from liquent_platform.application.health import Readiness
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import (
    ManifestHandoffSupervisorEngineApiProcessBundle,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_owner import (
    ManifestHandoffSupervisorEngineApiProcessOwner,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import (
    ManifestHandoffSupervisorEngineApiProcessPhase,
    ManifestHandoffSupervisorEngineApiProcessStatus,
    ManifestHandoffSupervisorEngineApiReadinessProbe,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import (
    ManifestHandoffSupervisorEngineApiServeResult,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_signal_run import (
    SignalOwnedManifestHandoffSupervisorEngineApiRun,
)


def _bundle(run_method=None):
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    inner = type("Inner", (), {})()
    inner._status = status
    run = object.__new__(SignalOwnedManifestHandoffSupervisorEngineApiRun)
    run._process = inner
    run._signals = object()
    if run_method is not None:
        run.run = run_method
    probe = ManifestHandoffSupervisorEngineApiReadinessProbe(status)
    return ManifestHandoffSupervisorEngineApiProcessBundle(run, status, probe)


def test_entrypoint_uses_exactly_one_bundle_and_its_run(monkeypatch) -> None:
    settings = type("Settings", (), {"maximum_exchanges": 10})()
    process = type("Process", (), {})()
    process.runs = 0

    def run():
        process.runs += 1
        return ManifestHandoffSupervisorEngineApiServeResult(2, "stopped")

    process.run = run
    bundle = type("Bundle", (), {"process_run": process})()
    calls = []
    monkeypatch.setattr(
        entrypoint, "load_manifest_handoff_supervisor_engine_api_proxy_settings",
        lambda path: calls.append(("load", path)) or settings,
    )
    monkeypatch.setattr(
        entrypoint, "compose_manifest_handoff_supervisor_engine_api_proxy_bundle",
        lambda value: calls.append(("bundle", value)) or bundle,
    )
    result = entrypoint.run_manifest_handoff_supervisor_engine_api_proxy(
        Path("/private/proxy.env")
    )
    assert result.exchanges == 2
    assert calls == [("load", Path("/private/proxy.env")), ("bundle", settings)]
    assert process.runs == 1


def test_owner_claims_run_once_even_with_concurrent_callers(monkeypatch) -> None:
    bundle = _bundle()
    entered = threading.Event()
    release = threading.Event()

    def run(self):
        entered.set()
        release.wait(2)
        return ManifestHandoffSupervisorEngineApiServeResult(0, "stopped")

    monkeypatch.setattr(SignalOwnedManifestHandoffSupervisorEngineApiRun, "run", run)
    owner = ManifestHandoffSupervisorEngineApiProcessOwner(bundle)
    outcomes = []

    def invoke():
        try:
            owner.run()
            outcomes.append("completed")
        except ManifestHandoffRegistryUnavailable:
            outcomes.append("rejected")

    first = threading.Thread(target=invoke)
    first.start()
    assert entered.wait(1)
    second = threading.Thread(target=invoke)
    second.start()
    second.join()
    release.set()
    first.join()
    assert sorted(outcomes) == ["completed", "rejected"]


def test_health_reads_do_not_wait_for_running_claim(monkeypatch) -> None:
    bundle = _bundle()
    entered = threading.Event()
    release = threading.Event()

    def run(self):
        bundle.status.mark_starting()
        bundle.status.mark_serving()
        entered.set()
        release.wait(2)
        bundle.status.mark_stopping()
        bundle.status.mark_stopped()
        return ManifestHandoffSupervisorEngineApiServeResult(0, "stopped")

    monkeypatch.setattr(SignalOwnedManifestHandoffSupervisorEngineApiRun, "run", run)
    owner = ManifestHandoffSupervisorEngineApiProcessOwner(bundle)
    thread = threading.Thread(target=owner.run)
    thread.start()
    assert entered.wait(1)
    assert owner.readiness() == Readiness(
        True, "manifest_handoff_supervisor_engine_api_ready"
    )
    assert owner.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.SERVING
    release.set()
    thread.join()


def test_failed_run_consumes_claim_and_is_detail_free(monkeypatch) -> None:
    bundle = _bundle()
    monkeypatch.setattr(
        SignalOwnedManifestHandoffSupervisorEngineApiRun, "run",
        lambda self: (_ for _ in ()).throw(RuntimeError("private run detail")),
    )
    owner = ManifestHandoffSupervisorEngineApiProcessOwner(bundle)
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        owner.run()
    assert "private" not in str(caught.value)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        owner.run()


def test_owner_rejects_foreign_bundle_and_has_no_thread_start_surface() -> None:
    for value in (None, object(), "bundle"):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            ManifestHandoffSupervisorEngineApiProcessOwner(value)
    owner = ManifestHandoffSupervisorEngineApiProcessOwner(_bundle())
    assert repr(owner) == "ManifestHandoffSupervisorEngineApiProcessOwner()"
    for name in ("start", "join", "close", "server"):
        assert not hasattr(owner, name)
