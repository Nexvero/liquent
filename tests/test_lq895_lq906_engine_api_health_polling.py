from pathlib import Path
import socket

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_exchange import VerifiedManifestHandoffSupervisorEngineApiHealthExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_listener import ControlledManifestHandoffSupervisorEngineApiHealthListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_accept import BoundedManifestHandoffSupervisorEngineApiHealthPollAccept, ManifestHandoffSupervisorEngineApiHealthPollResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_listener import BoundedManifestHandoffSupervisorEngineApiHealthPollListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_loop import StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop


PATH = Path("/run/liquent/health.sock")


class Client:
    def __init__(self): self.timeout, self.closed = None, 0
    def set_inheritable(self, value): self.inheritable = value
    def settimeout(self, value): self.timeout = value
    def gettimeout(self): return self.timeout
    def getsockname(self): return str(PATH)
    def getpeername(self): return ""
    def close(self): self.closed += 1


class Listener:
    def __init__(self, outcome): self.outcome, self.timeout = outcome, 0.25
    def getsockname(self): return str(PATH)
    def gettimeout(self): return self.timeout
    def settimeout(self, value): self.timeout = value
    def accept(self):
        if self.outcome == "timeout": raise socket.timeout
        return self.outcome, ""


def operation():
    return BoundedManifestHandoffSupervisorEngineApiHealthPollAccept(
        socket_path=PATH, poll_timeout_seconds=.25, client_timeout_seconds=5,
        exchange=object.__new__(VerifiedManifestHandoffSupervisorEngineApiHealthExchange),
    )


def test_timeout_is_neutral_without_client_or_exchange(monkeypatch):
    calls = []
    monkeypatch.setattr(VerifiedManifestHandoffSupervisorEngineApiHealthExchange, "exchange", lambda *args: calls.append(1))
    assert operation().poll_one(Listener("timeout")) == ManifestHandoffSupervisorEngineApiHealthPollResult(False)
    assert calls == []


def test_client_is_exchanged_and_closed(monkeypatch):
    client, calls = Client(), []
    monkeypatch.setattr(VerifiedManifestHandoffSupervisorEngineApiHealthExchange, "exchange", lambda self, value: calls.append(value))
    assert operation().poll_one(Listener(client)).served
    assert calls == [client] and client.closed == 1 and client.timeout == 5.0


def test_poll_listener_sets_timeout_and_delegates_close(monkeypatch):
    active, calls = Listener("timeout"), []
    base = object.__new__(ControlledManifestHandoffSupervisorEngineApiHealthListener)
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiHealthListener, "open", lambda self: calls.append("open") or active)
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiHealthListener, "close", lambda self, value: calls.append(("close", value)))
    value = BoundedManifestHandoffSupervisorEngineApiHealthPollListener(base, poll_timeout_seconds=.25)
    assert value.open() is active and active.timeout == .25
    value.close(active)
    assert calls == ["open", ("close", active)]


def test_poll_loop_rechecks_stop_after_neutral_timeout(monkeypatch):
    decisions, events = iter((False, True)), []
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiHealthPollAccept, "poll_one", lambda self, listener: events.append("poll") or ManifestHandoffSupervisorEngineApiHealthPollResult(False))
    result = StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop(operation(), maximum_exchanges=3).run(object(), lambda: events.append("stop") or next(decisions))
    assert result.exchanges == 0 and result.reason == "stopped"
    assert events == ["stop", "poll", "stop"]


def test_only_served_results_count_toward_limit(monkeypatch):
    outcomes = iter((False, True, False, True))
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiHealthPollAccept, "poll_one", lambda self, listener: ManifestHandoffSupervisorEngineApiHealthPollResult(next(outcomes)))
    result = StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop(operation(), maximum_exchanges=2).run(object(), lambda: False)
    assert result.exchanges == 2 and result.reason == "exchange_limit"


def test_invalid_stop_or_poll_result_fails_closed(monkeypatch):
    loop = StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop(operation(), maximum_exchanges=1)
    with pytest.raises(ManifestHandoffRegistryUnavailable): loop.run(object(), lambda: None)
    monkeypatch.setattr(BoundedManifestHandoffSupervisorEngineApiHealthPollAccept, "poll_one", lambda *args: object())
    with pytest.raises(ManifestHandoffRegistryUnavailable): loop.run(object(), lambda: False)
