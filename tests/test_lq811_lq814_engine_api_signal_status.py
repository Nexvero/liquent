import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_run import (
    OwnedManifestHandoffSupervisorEngineApiProcessRun,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import (
    ManifestHandoffSupervisorEngineApiProcessPhase,
    ManifestHandoffSupervisorEngineApiProcessStatus,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import (
    ManifestHandoffSupervisorEngineApiServeResult,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_signal_run import (
    SignalOwnedManifestHandoffSupervisorEngineApiRun,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import (
    OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
)


def _operation():
    status = ManifestHandoffSupervisorEngineApiProcessStatus()
    process = object.__new__(OwnedManifestHandoffSupervisorEngineApiProcessRun)
    process._status = status
    process._defer_terminal = True
    signals = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    return SignalOwnedManifestHandoffSupervisorEngineApiRun(signals, process), status


def _successful_process(self, stop):
    self._status.mark_starting()
    self._status.mark_serving()
    self._status.mark_stopping()
    return ManifestHandoffSupervisorEngineApiServeResult(2, "stopped")


def test_stopped_is_published_only_after_successful_signal_restore(monkeypatch) -> None:
    operation, status = _operation()
    observed = []
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "install", lambda self: observed.append(("install", status.snapshot().phase)),
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiProcessRun,
        "run", _successful_process,
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "restore", lambda self: observed.append(("restore", status.snapshot().phase)),
    )
    result = operation.run()
    assert result == ManifestHandoffSupervisorEngineApiServeResult(2, "stopped")
    assert observed == [
        ("install", ManifestHandoffSupervisorEngineApiProcessPhase.INITIAL),
        ("restore", ManifestHandoffSupervisorEngineApiProcessPhase.STOPPING),
    ]
    assert status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.STOPPED


def test_signal_install_failure_marks_initial_status_failed(monkeypatch) -> None:
    operation, status = _operation()
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "install",
        lambda self: (_ for _ in ()).throw(RuntimeError("private install detail")),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation.run()
    assert status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.FAILED


def test_signal_restore_failure_replaces_stopping_with_failed(monkeypatch) -> None:
    operation, status = _operation()
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "install", lambda self: None,
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiProcessRun,
        "run", _successful_process,
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "restore",
        lambda self: (_ for _ in ()).throw(RuntimeError("private restore detail")),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation.run()
    assert status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.FAILED


def test_inner_failed_status_is_preserved_after_signal_restore(monkeypatch) -> None:
    operation, status = _operation()
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "install", lambda self: None,
    )

    def fail(self, stop):
        self._status.mark_starting()
        self._status.mark_failed()
        raise RuntimeError("private run detail")

    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiProcessRun, "run", fail)
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "restore", lambda self: None,
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation.run()
    assert status.snapshot().phase is ManifestHandoffSupervisorEngineApiProcessPhase.FAILED


def test_deferred_process_cannot_be_finalized_with_wrong_shape_or_twice() -> None:
    operation, status = _operation()
    process = operation._process
    for value in (None, 1, "true"):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            process.finalize_outer_run(value)
    status.mark_starting()
    status.mark_serving()
    status.mark_stopping()
    process.finalize_outer_run(True)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        process.finalize_outer_run(True)


def test_non_deferred_direct_process_rejects_outer_finalization() -> None:
    process = object.__new__(OwnedManifestHandoffSupervisorEngineApiProcessRun)
    process._status = ManifestHandoffSupervisorEngineApiProcessStatus()
    process._defer_terminal = False
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        process.finalize_outer_run(False)
