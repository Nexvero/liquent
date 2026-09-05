import os
from pathlib import Path
import socket
import stat
import struct

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_peer import LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_exchange import ClosedManifestHandoffSupervisorEngineApiExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_gate import ClosedManifestHandoffSupervisorEngineApiGate
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import ClosedManifestHandoffSupervisorCreateRequestPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_verified_exchange import VerifiedManifestHandoffSupervisorEngineApiExchange


CLIENT_PATH = Path("/run/liquent/engine.sock")
DAEMON_PATH = Path("/var/run/docker.sock")
CONTAINER = "a" * 64


class Facts:
    st_mode = stat.S_IFSOCK | 0o660
    st_dev = 71

    def __init__(self, inode):
        self.st_ino = inode


class UnixStream:
    family = socket.AF_UNIX
    type = socket.SOCK_STREAM

    def __init__(self, descriptor, local, peer, credentials, incoming=()):
        self.descriptor = descriptor
        self.local, self.peer = local, peer
        self.credentials = credentials
        self.incoming = list(incoming)
        self.sent = bytearray()
        self.timeout = 5.0
        self.accepting = 0
        self.kernel_reads = 0
        self.io_reads = 0
        self.closed = 0

    def fileno(self):
        return self.descriptor

    def gettimeout(self):
        return self.timeout

    def getsockname(self):
        return self.local

    def getpeername(self):
        return self.peer

    def getsockopt(self, level, option, length=None):
        self.kernel_reads += 1
        if option == socket.SO_ACCEPTCONN:
            return self.accepting
        return struct.pack("3i", *self.credentials)

    def recv(self, maximum):
        self.io_reads += 1
        if not self.incoming:
            return b""
        value = self.incoming.pop(0)
        if len(value) > maximum:
            self.incoming.insert(0, value[maximum:])
            value = value[:maximum]
        return value

    def send(self, value):
        self.sent.extend(value)
        return len(value)

    def close(self):
        self.closed += 1


def request():
    return (
        f"GET /v1.45/containers/{CONTAINER}/json HTTP/1.1\r\n".encode()
        + b"host: localhost\r\naccept: application/json\r\n"
        + b"connection: close\r\n\r\n"
    )


def response(status=404):
    return f"HTTP/1.1 {status} status\r\n\r\n".encode()


def composition():
    create = ClosedManifestHandoffSupervisorCreateRequestPolicy(
        control_root=Path("/srv/liquent/control"),
        source_root=Path("/srv/liquent/source"),
        target_root=Path("/srv/liquent/target"),
        writer_command="writer-wrapper", recovery_command="recovery-wrapper",
        wrapper_uid=10002, wrapper_gid=10003,
    )
    return VerifiedManifestHandoffSupervisorEngineApiExchange(
        LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy(
            local_socket=CLIENT_PATH, client_uid=10001, client_gid=10002,
            timeout_seconds=5.0,
        ),
        LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy(
            daemon_socket=DAEMON_PATH, daemon_uid=0, daemon_gid=998,
            timeout_seconds=5.0,
        ),
        ClosedManifestHandoffSupervisorEngineApiExchange(
            ClosedManifestHandoffSupervisorEngineApiGate(create)
        ),
    )


def streams(client_credentials=(700, 10001, 10002), daemon_credentials=(800, 0, 998)):
    return (
        UnixStream(11, str(CLIENT_PATH), "", client_credentials, (request(),)),
        UnixStream(12, "", str(DAEMON_PATH), daemon_credentials, (response(),)),
    )


@pytest.fixture(autouse=True)
def descriptor_facts(monkeypatch):
    monkeypatch.setattr(os, "fstat", lambda descriptor: Facts(descriptor + 100))
    monkeypatch.setattr(os, "get_inheritable", lambda descriptor: False)


def test_both_kernel_peers_are_resolved_before_the_exchange() -> None:
    client, daemon = streams()
    composition().exchange(client, daemon)
    assert client.kernel_reads >= 2 and daemon.kernel_reads >= 2
    assert client.io_reads >= 1 and daemon.io_reads >= 1
    assert bytes(daemon.sent) == request()
    assert bytes(client.sent) == (
        b"HTTP/1.1 404 Not Found\r\nconnection: close\r\n\r\n"
    )
    assert client.closed == daemon.closed == 0


def test_rejected_client_peer_causes_no_stream_io() -> None:
    client, daemon = streams(client_credentials=(700, 10003, 10002))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        composition().exchange(client, daemon)
    assert client.io_reads == daemon.io_reads == 0
    assert not client.sent and not daemon.sent
    assert daemon.kernel_reads == 0


def test_rejected_daemon_peer_causes_no_stream_io() -> None:
    client, daemon = streams(daemon_credentials=(800, 1, 998))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        composition().exchange(client, daemon)
    assert client.kernel_reads >= 2 and daemon.kernel_reads >= 2
    assert client.io_reads == daemon.io_reads == 0
    assert not client.sent and not daemon.sent


def test_same_descriptor_for_distinct_objects_is_rejected_before_io() -> None:
    client, daemon = streams()
    daemon.descriptor = client.descriptor
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        composition().exchange(client, daemon)
    assert client.io_reads == daemon.io_reads == 0


def test_same_stream_is_rejected_before_kernel_or_stream_io() -> None:
    client, _ = streams()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        composition().exchange(client, client)
    assert client.kernel_reads == client.io_reads == 0


def test_post_verification_descriptor_change_is_rejected(monkeypatch) -> None:
    client, daemon = streams()
    original = daemon.fileno
    calls = 0

    def changing():
        nonlocal calls
        calls += 1
        return original() if calls < 3 else 99

    daemon.fileno = changing
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        composition().exchange(client, daemon)
    assert client.io_reads == daemon.io_reads == 0


def test_kernel_errors_are_detail_free_and_streams_remain_external() -> None:
    client, daemon = streams()
    client.getsockopt = lambda *args: (_ for _ in ()).throw(RuntimeError("secret"))
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        composition().exchange(client, daemon)
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "secret" not in str(caught.value)
    assert client.closed == daemon.closed == 0


def test_composition_has_no_listener_connect_timeout_or_close_surface() -> None:
    value = composition()
    assert repr(value) == "VerifiedManifestHandoffSupervisorEngineApiExchange()"
    for name in ("listen", "bind", "accept", "connect", "settimeout", "close"):
        assert not hasattr(value, name)
