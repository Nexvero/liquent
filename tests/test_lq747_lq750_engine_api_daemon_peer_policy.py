import os
from pathlib import Path
import socket
import stat
import struct

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_peer import (
    LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy,
)


DAEMON = Path("/var/run/docker.sock")


class Facts:
    st_mode = stat.S_IFSOCK | 0o660
    st_dev = 31
    st_ino = 41


class ConnectedDaemon:
    family = socket.AF_UNIX
    type = socket.SOCK_STREAM

    def __init__(self, *, pid=500, uid=0, gid=998, timeout=5.0):
        self.pid, self.uid, self.gid = pid, uid, gid
        self.timeout = timeout
        self.descriptor = 10
        self.local = ""
        self.peer = str(DAEMON)
        self.accepting = 0
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
        if option == socket.SO_ACCEPTCONN:
            return self.accepting
        return struct.pack("3i", self.pid, self.uid, self.gid)

    def close(self):
        self.closed += 1


def policy(uid=0):
    return LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy(
        daemon_socket=DAEMON, daemon_uid=uid, daemon_gid=998,
        timeout_seconds=5.0,
    )


@pytest.fixture(autouse=True)
def descriptor_facts(monkeypatch):
    monkeypatch.setattr(os, "fstat", lambda descriptor: Facts())
    monkeypatch.setattr(os, "get_inheritable", lambda descriptor: False)


def test_exact_connected_daemon_facts_authorize_root_owned_peer() -> None:
    stream = ConnectedDaemon()
    result = policy().authorize(stream)
    assert (result.descriptor, result.process_id) == (10, 500)
    assert (result.user_id, result.group_id) == (0, 998)
    assert result.daemon_socket == DAEMON
    assert stream.closed == 0


def test_positive_non_root_daemon_uid_can_be_bound_explicitly() -> None:
    result = policy(uid=100).authorize(ConnectedDaemon(uid=100))
    assert result.user_id == 100


@pytest.mark.parametrize("mutation", (
    lambda value: setattr(value, "family", socket.AF_INET),
    lambda value: setattr(value, "type", socket.SOCK_DGRAM),
    lambda value: setattr(value, "timeout", None),
    lambda value: setattr(value, "descriptor", -1),
    lambda value: setattr(value, "local", "/tmp/client.sock"),
    lambda value: setattr(value, "peer", "/var/run/other.sock"),
    lambda value: setattr(value, "accepting", 1),
    lambda value: setattr(value, "pid", 0),
    lambda value: setattr(value, "uid", 1),
    lambda value: setattr(value, "gid", 999),
))
def test_any_endpoint_descriptor_or_daemon_identity_drift_fails_closed(mutation) -> None:
    stream = ConnectedDaemon()
    mutation(stream)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(stream)
    assert stream.closed == 0


def test_regular_or_inheritable_descriptor_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(os, "fstat", lambda descriptor: type("F", (), {
        "st_mode": stat.S_IFREG | 0o660, "st_dev": 31, "st_ino": 41,
    })())
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(ConnectedDaemon())
    monkeypatch.setattr(os, "fstat", lambda descriptor: Facts())
    monkeypatch.setattr(os, "get_inheritable", lambda descriptor: True)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(ConnectedDaemon())


def test_inode_swap_during_kernel_resolution_fails_closed(monkeypatch) -> None:
    changed = type("F", (), {
        "st_mode": stat.S_IFSOCK | 0o660, "st_dev": 31, "st_ino": 42,
    })()
    calls = iter((Facts(), changed))
    monkeypatch.setattr(os, "fstat", lambda descriptor: next(calls))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(ConnectedDaemon())


def test_malformed_kernel_credentials_are_detail_free() -> None:
    stream = ConnectedDaemon()
    stream.getsockopt = lambda *args: 0 if args[1] == socket.SO_ACCEPTCONN else b"secret"
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        policy().authorize(stream)
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("values", (
    {"daemon_socket": Path("relative.sock"), "daemon_uid": 0, "daemon_gid": 1, "timeout_seconds": 1},
    {"daemon_socket": Path("/"), "daemon_uid": 0, "daemon_gid": 1, "timeout_seconds": 1},
    {"daemon_socket": DAEMON, "daemon_uid": -1, "daemon_gid": 1, "timeout_seconds": 1},
    {"daemon_socket": DAEMON, "daemon_uid": 0, "daemon_gid": 0, "timeout_seconds": 1},
    {"daemon_socket": DAEMON, "daemon_uid": 0, "daemon_gid": 1, "timeout_seconds": False},
))
def test_invalid_configuration_fails_before_stream_inspection(values) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy(**values)


def test_policy_has_no_connect_mutation_shutdown_or_close_surface() -> None:
    surface = vars(LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy)
    for name in ("connect", "settimeout", "set_inheritable", "shutdown", "close"):
        assert name not in surface
