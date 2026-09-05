import signal
import threading

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import (
    OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
)


@pytest.fixture
def signals(monkeypatch):
    previous = {signal.SIGTERM: object(), signal.SIGINT: object()}
    current = dict(previous)
    calls = []

    def getsignal(number):
        calls.append(("get", number))
        return current[number]

    def install(number, handler):
        calls.append(("set", number, handler))
        old = current[number]
        current[number] = handler
        return old

    monkeypatch.setattr(signal, "getsignal", getsignal)
    monkeypatch.setattr(signal, "signal", install)
    return previous, current, calls


def test_construction_and_requested_read_have_no_global_effect(signals) -> None:
    _, _, calls = signals
    source = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    assert source.requested() is False
    assert calls == []


@pytest.mark.parametrize("number", (signal.SIGTERM, signal.SIGINT))
def test_installed_minimal_handler_sets_only_local_stop_state(signals, number) -> None:
    previous, current, _ = signals
    source = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    source.install()
    assert source.requested() is False
    current[number](number, object())
    assert source.requested() is True
    assert current[number] != previous[number]


def test_restore_reinstates_both_handlers_in_reverse_order(signals) -> None:
    previous, current, calls = signals
    source = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    source.install()
    calls.clear()
    source.restore()
    assert current == previous
    assert [item[1] for item in calls] == [signal.SIGINT, signal.SIGTERM]
    assert source.requested() is False


def test_second_install_and_second_restore_fail_closed(signals) -> None:
    source = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    source.install()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        source.install()
    source.restore()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        source.restore()


def test_reinstall_resets_prior_requested_state(signals) -> None:
    _, current, _ = signals
    source = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    source.install()
    current[signal.SIGTERM](signal.SIGTERM, None)
    assert source.requested() is True
    source.restore()
    source.install()
    assert source.requested() is False


def test_partial_install_failure_rolls_back_first_handler(signals, monkeypatch) -> None:
    previous, current, calls = signals
    original = signal.signal

    def fail_second(number, handler):
        if number == signal.SIGINT and handler != previous[number]:
            raise RuntimeError("secret")
        return original(number, handler)

    monkeypatch.setattr(signal, "signal", fail_second)
    source = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        source.install()
    assert current == previous
    assert "secret" not in str(caught.value)
    assert any(item[0] == "set" for item in calls)


def test_restore_attempts_both_handlers_even_if_one_fails(signals, monkeypatch) -> None:
    previous, current, calls = signals
    source = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    source.install()
    original = signal.signal

    def fail_int(number, handler):
        if number == signal.SIGINT and handler is previous[number]:
            raise RuntimeError("secret")
        return original(number, handler)

    monkeypatch.setattr(signal, "signal", fail_int)
    calls.clear()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        source.restore()
    assert current[signal.SIGTERM] is previous[signal.SIGTERM]
    assert any(item[1] == signal.SIGTERM for item in calls)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        source.restore()


def test_install_outside_main_thread_fails_before_signal_reads(signals, monkeypatch) -> None:
    _, _, calls = signals
    monkeypatch.setattr(threading, "current_thread", lambda: object())
    monkeypatch.setattr(threading, "main_thread", lambda: object())
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        OwnedManifestHandoffSupervisorEngineApiSignalStopSource().install()
    assert calls == []


def test_unknown_or_post_restore_handler_call_has_no_effect(signals) -> None:
    source = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    source.install()
    handler = source._handle
    handler(999, None)
    assert source.requested() is False
    source.restore()
    handler(signal.SIGTERM, None)
    assert source.requested() is False


def test_source_has_no_kill_raise_signal_thread_or_close_surface() -> None:
    source = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
    assert repr(source) == "OwnedManifestHandoffSupervisorEngineApiSignalStopSource()"
    for name in ("kill", "raise_signal", "thread", "run", "close"):
        assert not hasattr(source, name)
