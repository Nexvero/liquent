from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_accept import ControlledManifestHandoffSupervisorEngineApiHealthAccept
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_exchange import VerifiedManifestHandoffSupervisorEngineApiHealthExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_listener import ControlledManifestHandoffSupervisorEngineApiHealthListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_serve_loop import BoundedManifestHandoffSupervisorEngineApiHealthServeLoop, ManifestHandoffSupervisorEngineApiHealthServeResult


PATH = Path("/run/liquent/health.sock")


class Client:
    def __init__(self):
        self.timeout = None
        self.closed = 0
    def set_inheritable(self, value): self.inheritable = value
    def settimeout(self, value): self.timeout = value
    def gettimeout(self): return self.timeout
    def getsockname(self): return str(PATH)
    def getpeername(self): return ""
    def close(self): self.closed += 1


class Listener:
    def __init__(self, client): self.client, self.accepts = client, 0
    def getsockname(self): return str(PATH)
    def accept(self):
        self.accepts += 1
        return self.client, ""


def operation():
    exchange = object.__new__(VerifiedManifestHandoffSupervisorEngineApiHealthExchange)
    return ControlledManifestHandoffSupervisorEngineApiHealthAccept(
        socket_path=PATH, client_timeout_seconds=5, exchange=exchange,
    )


def test_accept_configures_exchanges_and_closes_once(monkeypatch):
    client, calls = Client(), []
    monkeypatch.setattr(VerifiedManifestHandoffSupervisorEngineApiHealthExchange,
                        "exchange", lambda self, stream: calls.append(stream))
    operation().serve_one(Listener(client))
    assert calls == [client] and client.timeout == 5.0 and client.closed == 1


def test_accept_failure_is_detail_free_and_still_closes(monkeypatch):
    client = Client()
    monkeypatch.setattr(VerifiedManifestHandoffSupervisorEngineApiHealthExchange,
                        "exchange", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")))
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().serve_one(Listener(client))
    assert client.closed == 1 and "secret" not in str(caught.value)


def test_health_listener_delegates_exact_lifecycle(monkeypatch):
    listener, calls = object(), []
    monkeypatch.setattr("liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener.ControlledManifestHandoffSupervisorEngineApiListener.open", lambda self: calls.append("open") or listener)
    monkeypatch.setattr("liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener.ControlledManifestHandoffSupervisorEngineApiListener.close", lambda self, value: calls.append(("close", value)))
    value = ControlledManifestHandoffSupervisorEngineApiHealthListener(
        socket_path=PATH, socket_uid=100, client_gid=101, parent_uid=100,
        parent_gid=101, backlog=8,
    )
    assert value.open() is listener
    value.close(listener)
    assert calls == ["open", ("close", listener)]


def test_loop_stops_between_sequential_accepts(monkeypatch):
    events, decisions = [], iter((False, False, True))
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiHealthAccept,
                        "serve_one", lambda self, listener: events.append("accept"))
    result = BoundedManifestHandoffSupervisorEngineApiHealthServeLoop(
        operation(), maximum_exchanges=5,
    ).run(object(), lambda: events.append("stop") or next(decisions))
    assert result == ManifestHandoffSupervisorEngineApiHealthServeResult(2, "stopped")
    assert events == ["stop", "accept", "stop", "accept", "stop"]


def test_loop_bound_and_failure_are_closed(monkeypatch):
    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiHealthAccept,
                        "serve_one", lambda *args: None)
    value = BoundedManifestHandoffSupervisorEngineApiHealthServeLoop(
        operation(), maximum_exchanges=2,
    )
    assert value.run(object(), lambda: False) == ManifestHandoffSupervisorEngineApiHealthServeResult(2, "exchange_limit")
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        value.run(object(), lambda: None)


def test_surfaces_remain_separate():
    assert repr(operation()) == "ControlledManifestHandoffSupervisorEngineApiHealthAccept()"
    for name in ("open", "listen", "run", "close"):
        assert not hasattr(operation(), name)
