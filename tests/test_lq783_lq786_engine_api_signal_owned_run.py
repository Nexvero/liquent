import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_run import OwnedManifestHandoffSupervisorEngineApiProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import ManifestHandoffSupervisorEngineApiServeResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_signal_run import SignalOwnedManifestHandoffSupervisorEngineApiRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import OwnedManifestHandoffSupervisorEngineApiSignalStopSource


def operation():
    signals = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    process = object.__new__(OwnedManifestHandoffSupervisorEngineApiProcessRun)
    return SignalOwnedManifestHandoffSupervisorEngineApiRun(signals, process)


def test_install_run_with_bound_stop_method_then_restore(monkeypatch) -> None:
    events = []
    expected = ManifestHandoffSupervisorEngineApiServeResult(2, "stopped")

    def install(self):
        events.append(("install", self))

    def run(self, stop):
        events.append(("run", self, stop.__self__, stop.__func__))
        return expected

    def restore(self):
        events.append(("restore", self))

    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "install", install)
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiProcessRun, "run", run)
    monkeypatch.setattr(OwnedManifestHandoffSupervisorEngineApiSignalStopSource, "restore", restore)
    value = operation()
    assert value.run() == expected
    assert [item[0] for item in events] == ["install", "run", "restore"]
    assert events[1][2] is events[0][1]
    assert events[1][3] is OwnedManifestHandoffSupervisorEngineApiSignalStopSource.requested


def test_install_failure_has_no_run_or_restore_effect(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "install", lambda self: (_ for _ in ()).throw(RuntimeError("install secret")),
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiProcessRun,
        "run", lambda *args: events.append("run"),
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "restore", lambda *args: events.append("restore"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().run()
    assert events == []
    assert "secret" not in str(caught.value)


def test_process_failure_restores_signals_once(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "install", lambda self: events.append("install"),
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiProcessRun,
        "run", lambda *args: (_ for _ in ()).throw(RuntimeError("run secret")),
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "restore", lambda self: events.append("restore"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().run()
    assert events == ["install", "restore"]
    assert "secret" not in str(caught.value)


def test_restore_failure_after_success_prevents_success(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "install", lambda self: events.append("install"),
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiProcessRun,
        "run", lambda *args: ManifestHandoffSupervisorEngineApiServeResult(
            1, "exchange_limit"
        ),
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "restore", lambda self: (_ for _ in ()).throw(RuntimeError("restore secret")),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().run()
    assert events == ["install"]
    assert "secret" not in str(caught.value)


def test_run_and_restore_failure_remain_one_detail_free_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "install", lambda self: None,
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiProcessRun,
        "run", lambda *args: (_ for _ in ()).throw(RuntimeError("run secret")),
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "restore", lambda self: (_ for _ in ()).throw(RuntimeError("restore secret")),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().run()
    assert str(caught.value) == "manifest_handoff_registry_unavailable"


def test_wrong_process_result_is_rejected_after_restore(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "install", lambda self: None,
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiProcessRun,
        "run", lambda *args: object(),
    )
    monkeypatch.setattr(
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        "restore", lambda self: events.append("restore"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation().run()
    assert events == ["restore"]


@pytest.mark.parametrize("signals,process", (
    (object(), object.__new__(OwnedManifestHandoffSupervisorEngineApiProcessRun)),
    (OwnedManifestHandoffSupervisorEngineApiSignalStopSource(), object()),
))
def test_only_concrete_signal_and_process_owners_can_be_composed(signals, process) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        SignalOwnedManifestHandoffSupervisorEngineApiRun(signals, process)


def test_signal_owned_run_has_no_main_exit_signal_or_close_surface() -> None:
    value = operation()
    assert repr(value) == "SignalOwnedManifestHandoffSupervisorEngineApiRun()"
    for name in ("main", "exit", "signal", "install", "restore", "close"):
        assert not hasattr(value, name)
