import os
from pathlib import Path
import socket
import stat
import struct

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import (
    LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
)


LOCAL = Path("/run/liquent/supervisor-engine.sock")


class Facts:
    st_mode = stat.S_IFSOCK | 0o660
    st_dev = 11
    st_ino = 22


class AcceptedSocket:
    family = socket.AF_UNIX
    type = socket.SOCK_STREAM

    def __init__(self, *, pid=400, uid=10001, gid=10002, timeout=5.0):
        self.pid, self.uid, self.gid = pid, uid, gid
        self.timeout = timeout
        self.descriptor = 9
        self.local = str(LOCAL)
        self.peer = ""
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


def policy():
    return LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy(
        local_socket=LOCAL, client_uid=10001, client_gid=10002,
        timeout_seconds=5.0,
    )


@pytest.fixture(autouse=True)
def descriptor_facts(monkeypatch):
    monkeypatch.setattr(os, "fstat", lambda descriptor: Facts())
    monkeypatch.setattr(os, "get_inheritable", lambda descriptor: False)


def test_exact_current_kernel_facts_authorize_the_accepted_peer() -> None:
    stream = AcceptedSocket()
    result = policy().authorize(stream)
    assert (result.descriptor, result.process_id) == (9, 400)
    assert (result.user_id, result.group_id) == (10001, 10002)
    assert result.local_socket == LOCAL
    assert stream.closed == 0


@pytest.mark.parametrize("mutation", (
    lambda value: setattr(value, "family", socket.AF_INET),
    lambda value: setattr(value, "type", socket.SOCK_DGRAM),
    lambda value: setattr(value, "timeout", None),
    lambda value: setattr(value, "descriptor", -1),
    lambda value: setattr(value, "local", "/run/other.sock"),
    lambda value: setattr(value, "accepting", 1),
    lambda value: setattr(value, "pid", 0),
    lambda value: setattr(value, "uid", 10003),
    lambda value: setattr(value, "gid", 10003),
))
def test_any_socket_or_peer_fact_drift_fails_closed(mutation) -> None:
    stream = AcceptedSocket()
    mutation(stream)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(stream)
    assert stream.closed == 0


def test_non_socket_or_inheritable_descriptor_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(os, "fstat", lambda descriptor: type("F", (), {
        "st_mode": stat.S_IFREG | 0o660, "st_dev": 11, "st_ino": 22,
    })())
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(AcceptedSocket())
    monkeypatch.setattr(os, "fstat", lambda descriptor: Facts())
    monkeypatch.setattr(os, "get_inheritable", lambda descriptor: True)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(AcceptedSocket())


def test_descriptor_or_inode_swap_during_resolution_fails_closed(monkeypatch) -> None:
    calls = iter((Facts(), type("F", (), {
        "st_mode": stat.S_IFSOCK | 0o660, "st_dev": 11, "st_ino": 23,
    })()))
    monkeypatch.setattr(os, "fstat", lambda descriptor: next(calls))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        policy().authorize(AcceptedSocket())


def test_malformed_peer_credentials_are_detail_free() -> None:
    stream = AcceptedSocket()
    stream.getsockopt = lambda *args: 0 if args[1] == socket.SO_ACCEPTCONN else b"secret"
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        policy().authorize(stream)
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("values", (
    {"local_socket": Path("relative.sock"), "client_uid": 1, "client_gid": 1, "timeout_seconds": 1},
    {"local_socket": Path("/"), "client_uid": 1, "client_gid": 1, "timeout_seconds": 1},
    {"local_socket": LOCAL, "client_uid": 0, "client_gid": 1, "timeout_seconds": 1},
    {"local_socket": LOCAL, "client_uid": 1, "client_gid": 0, "timeout_seconds": 1},
    {"local_socket": LOCAL, "client_uid": 1, "client_gid": 1, "timeout_seconds": 0},
))
def test_invalid_policy_configuration_fails_before_inspection(values) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy(**values)


def test_policy_has_no_accept_mutation_connect_or_close_surface() -> None:
    surface = vars(LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy)
    for name in ("accept", "settimeout", "set_inheritable", "connect", "close"):
        assert name not in surface
