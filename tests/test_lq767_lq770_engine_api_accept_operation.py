import os
from pathlib import Path
import socket
import stat

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_accept import ControlledManifestHandoffSupervisorEngineApiAccept
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_connected_exchange import ConnectedManifestHandoffSupervisorEngineApiExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_connector import ControlledManifestHandoffSupervisorEngineApiDaemonConnector
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_peer import LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_exchange import ClosedManifestHandoffSupervisorEngineApiExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_gate import ClosedManifestHandoffSupervisorEngineApiGate
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import ClosedManifestHandoffSupervisorCreateRequestPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_verified_exchange import VerifiedManifestHandoffSupervisorEngineApiExchange


PATH = Path("/run/liquent/engine.sock")
DAEMON = Path("/var/run/docker.sock")


class Facts:
    st_mode = stat.S_IFSOCK | 0o660


class Client:
    family = socket.AF_UNIX
    type = socket.SOCK_STREAM

    def __init__(self):
        self.descriptor = 22
        self.timeout = None
        self.local = str(PATH)
        self.peer = ""
        self.accepting = 0
        self.calls = []
        self.closed = 0
        self.close_failure = False

    def set_inheritable(self, value):
        self.calls.append(("inheritable", value))

    def settimeout(self, value):
        self.calls.append(("timeout", value))
        self.timeout = value

    def fileno(self):
        return self.descriptor

    def gettimeout(self):
        return self.timeout

    def getsockname(self):
        return self.local

    def getpeername(self):
        return self.peer

    def getsockopt(self, level, option):
        return self.accepting

    def close(self):
        self.closed += 1
        if self.close_failure:
            raise RuntimeError("close secret")


class Listener:
    family = socket.AF_UNIX
    type = socket.SOCK_STREAM

    def __init__(self, client):
        self.client = client
        self.descriptor = 21
        self.local = str(PATH)
        self.accepting = 1
        self.accepts = 0
        self.closed = 0
        self.failure = False
        self.address = ""

    def fileno(self):
        return self.descriptor

    def getsockname(self):
        return self.local

    def getsockopt(self, level, option):
        return self.accepting

    def accept(self):
        self.accepts += 1
        if self.failure:
            raise RuntimeError("accept secret")
        return self.client, self.address

    def close(self):
        self.closed += 1


def connected_exchange():
    create = ClosedManifestHandoffSupervisorCreateRequestPolicy(
        control_root=Path("/srv/liquent/control"),
        source_root=Path("/srv/liquent/source"),
        target_root=Path("/srv/liquent/target"),
        writer_command="writer-wrapper", recovery_command="recovery-wrapper",
        wrapper_uid=10002, wrapper_gid=10003,
    )
    verified = VerifiedManifestHandoffSupervisorEngineApiExchange(
        LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy(
            local_socket=PATH, client_uid=10001, client_gid=10002,
            timeout_seconds=5.0,
        ),
        LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy(
            daemon_socket=DAEMON, daemon_uid=0, daemon_gid=998,
            timeout_seconds=5.0,
        ),
        ClosedManifestHandoffSupervisorEngineApiExchange(
            ClosedManifestHandoffSupervisorEngineApiGate(create)
        ),
    )
    connector = ControlledManifestHandoffSupervisorEngineApiDaemonConnector(
        daemon_socket=DAEMON, timeout_seconds=5.0,
        socket_factory=lambda family, kind: None,
    )
    return ConnectedManifestHandoffSupervisorEngineApiExchange(connector, verified)


def operation():
    return ControlledManifestHandoffSupervisorEngineApiAccept(
        socket_path=PATH, client_timeout_seconds=5.0,
        exchange=connected_exchange(),
    )


@pytest.fixture(autouse=True)
def descriptor_facts(monkeypatch):
    monkeypatch.setattr(os, "fstat", lambda descriptor: Facts())
    monkeypatch.setattr(os, "get_inheritable", lambda descriptor: False)


def test_accept_setup_exchange_then_client_close_exactly_once(monkeypatch) -> None:
    client, calls = Client(), []
    listener = Listener(client)
    monkeypatch.setattr(
        ConnectedManifestHandoffSupervisorEngineApiExchange,
        "serve", lambda self, value: calls.append(value),
    )
    operation().serve_one(listener)
    assert listener.accepts == 1 and calls == [client]
    assert client.calls == [("inheritable", False), ("timeout", 5.0)]
    assert client.closed == 1 and listener.closed == 0


def test_listener_rejection_or_accept_failure_has_no_client_close(monkeypatch) -> None:
    client = Client()
    listener = Listener(client)
    listener.local = "/wrong.sock"
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation().serve_one(listener)
    assert listener.accepts == 0 and client.closed == 0
    listener.local = str(PATH)
    listener.failure = True
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().serve_one(listener)
    assert listener.accepts == 1 and client.closed == 0
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("mutation", (
    lambda value: setattr(value, "family", socket.AF_INET),
    lambda value: setattr(value, "type", socket.SOCK_DGRAM),
    lambda value: setattr(value, "descriptor", -1),
    lambda value: setattr(value, "local", "/wrong.sock"),
    lambda value: setattr(value, "peer", "/tmp/client.sock"),
    lambda value: setattr(value, "accepting", 1),
    lambda value: setattr(value, "settimeout", lambda timeout: None),
))
def test_client_setup_or_fact_failure_closes_client_without_exchange(
    monkeypatch, mutation,
) -> None:
    client, calls = Client(), []
    mutation(client)
    monkeypatch.setattr(
        ConnectedManifestHandoffSupervisorEngineApiExchange,
        "serve", lambda *args: calls.append("serve"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation().serve_one(Listener(client))
    assert client.closed == 1 and calls == []


def test_nonempty_accept_address_closes_client_before_exchange(monkeypatch) -> None:
    client, listener, calls = Client(), Listener(Client()), []
    listener.client = client
    listener.address = "/tmp/client.sock"
    monkeypatch.setattr(
        ConnectedManifestHandoffSupervisorEngineApiExchange,
        "serve", lambda *args: calls.append("serve"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        operation().serve_one(listener)
    assert client.closed == 1 and calls == []


def test_exchange_failure_still_closes_client_once(monkeypatch) -> None:
    client = Client()
    monkeypatch.setattr(
        ConnectedManifestHandoffSupervisorEngineApiExchange,
        "serve", lambda *args: (_ for _ in ()).throw(RuntimeError("exchange secret")),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().serve_one(Listener(client))
    assert client.closed == 1
    assert "secret" not in str(caught.value)


def test_client_close_failure_after_success_is_unavailable(monkeypatch) -> None:
    client = Client()
    client.close_failure = True
    monkeypatch.setattr(
        ConnectedManifestHandoffSupervisorEngineApiExchange, "serve", lambda *args: None,
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().serve_one(Listener(client))
    assert client.closed == 1
    assert "secret" not in str(caught.value)


def test_operation_has_no_listener_lifecycle_connect_loop_or_close_surface() -> None:
    value = operation()
    assert repr(value) == "ControlledManifestHandoffSupervisorEngineApiAccept()"
    for name in ("open", "listen", "bind", "connect", "run", "loop", "close"):
        assert not hasattr(value, name)
