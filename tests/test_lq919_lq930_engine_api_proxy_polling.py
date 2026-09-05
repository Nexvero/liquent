import socket

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_accept import ControlledManifestHandoffSupervisorEngineApiAccept, ManifestHandoffSupervisorEngineApiAcceptPollResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener import ControlledManifestHandoffSupervisorEngineApiListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_listener import BoundedManifestHandoffSupervisorEngineApiPollListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_loop import StopAwareManifestHandoffSupervisorEngineApiPollLoop


def accept_operation():
    return object.__new__(ControlledManifestHandoffSupervisorEngineApiAccept)


def test_poll_timeout_is_neutral_after_listener_validation(monkeypatch):
    value = accept_operation()
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiAccept, "_listener", lambda self, listener: None)
    listener = type("Listener", (), {"accept": lambda self: (_ for _ in ()).throw(socket.timeout())})()
    assert value.poll_one(listener) == ManifestHandoffSupervisorEngineApiAcceptPollResult(False)


def test_legacy_serve_one_still_maps_timeout_to_unavailable(monkeypatch):
    value = accept_operation()
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiAccept, "_listener", lambda self, listener: None)
    listener = type("Listener", (), {"accept": lambda self: (_ for _ in ()).throw(socket.timeout())})()
    with pytest.raises(ManifestHandoffRegistryUnavailable): value.serve_one(listener)


def test_poll_listener_sets_timeout_and_delegates_close(monkeypatch):
    active = type("Listener", (), {"timeout": None, "settimeout": lambda self, value: setattr(self, "timeout", value), "gettimeout": lambda self: self.timeout})()
    calls = []
    base = object.__new__(ControlledManifestHandoffSupervisorEngineApiListener)
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiListener, "open", lambda self: calls.append("open") or active)
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiListener, "close", lambda self, value: calls.append(("close", value)))
    value = BoundedManifestHandoffSupervisorEngineApiPollListener(base, poll_timeout_seconds=.25)
    assert value.open() is active and active.timeout == .25
    value.close(active)
    assert calls == ["open", ("close", active)]


def test_poll_loop_rechecks_stop_after_timeout(monkeypatch):
    events, stops = [], iter((False, True))
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiAccept, "poll_one", lambda self, listener: events.append("poll") or ManifestHandoffSupervisorEngineApiAcceptPollResult(False))
    result = StopAwareManifestHandoffSupervisorEngineApiPollLoop(accept_operation(), maximum_exchanges=2).run(object(), lambda: events.append("stop") or next(stops))
    assert result.exchanges == 0 and result.reason == "stopped"
    assert events == ["stop", "poll", "stop"]


def test_only_served_polls_count(monkeypatch):
    outcomes = iter((False, True, False, True))
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiAccept, "poll_one", lambda self, listener: ManifestHandoffSupervisorEngineApiAcceptPollResult(next(outcomes)))
    result = StopAwareManifestHandoffSupervisorEngineApiPollLoop(accept_operation(), maximum_exchanges=2).run(object(), lambda: False)
    assert result.exchanges == 2 and result.reason == "exchange_limit"


def test_invalid_stop_or_result_fails_closed(monkeypatch):
    loop = StopAwareManifestHandoffSupervisorEngineApiPollLoop(accept_operation(), maximum_exchanges=1)
    with pytest.raises(ManifestHandoffRegistryUnavailable): loop.run(object(), lambda: None)
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiAccept, "poll_one", lambda *args: object())
    with pytest.raises(ManifestHandoffRegistryUnavailable): loop.run(object(), lambda: False)
