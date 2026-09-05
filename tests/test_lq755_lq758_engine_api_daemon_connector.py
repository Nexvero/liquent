import os
from pathlib import Path
import socket
import stat

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_connector import (
    ControlledManifestHandoffSupervisorEngineApiDaemonConnector,
)


DAEMON = Path("/var/run/docker.sock")


class Facts:
    st_mode = stat.S_IFSOCK | 0o660


class Stream:
    family = socket.AF_UNIX
    type = socket.SOCK_STREAM

    def __init__(self):
        self.descriptor = 15
        self.timeout = None
        self.inheritable = None
        self.local = ""
        self.peer = str(DAEMON)
        self.calls = []
        self.closed = 0
        self.failure = None

    def set_inheritable(self, value):
        self.calls.append(("inheritable", value))
        self.inheritable = value
        if self.failure == "inheritable":
            raise RuntimeError("secret")

    def settimeout(self, value):
        self.calls.append(("timeout", value))
        self.timeout = value
        if self.failure == "timeout":
            raise RuntimeError("secret")

    def connect(self, path):
        self.calls.append(("connect", path))
        if self.failure == "connect":
            raise RuntimeError("secret")

    def fileno(self):
        return self.descriptor

    def gettimeout(self):
        return self.timeout

    def getsockname(self):
        return self.local

    def getpeername(self):
        return self.peer

    def close(self):
        self.closed += 1
        if self.failure == "close":
            raise RuntimeError("close detail")


def connector(stream):
    calls = []

    def factory(family, kind):
        calls.append((family, kind))
        return stream

    return ControlledManifestHandoffSupervisorEngineApiDaemonConnector(
        daemon_socket=DAEMON, timeout_seconds=5.0, socket_factory=factory,
    ), calls


@pytest.fixture(autouse=True)
def descriptor_facts(monkeypatch):
    monkeypatch.setattr(os, "fstat", lambda descriptor: Facts())
    monkeypatch.setattr(os, "get_inheritable", lambda descriptor: False)


def test_exact_one_shot_connect_transfers_open_stream_ownership() -> None:
    stream = Stream()
    value, factory_calls = connector(stream)
    assert value.connect() is stream
    assert len(factory_calls) == 1
    assert factory_calls[0][0] == socket.AF_UNIX
    assert factory_calls[0][1] & socket.SOCK_STREAM
    assert stream.calls == [
        ("inheritable", False), ("timeout", 5.0),
        ("connect", str(DAEMON)),
    ]
    assert stream.closed == 0


@pytest.mark.parametrize("failure", ("inheritable", "timeout", "connect"))
def test_setup_or_connect_failure_closes_partial_stream_once(failure) -> None:
    stream = Stream()
    stream.failure = failure
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        connector(stream)[0].connect()
    assert stream.closed == 1
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("mutation", (
    lambda value: setattr(value, "family", socket.AF_INET),
    lambda value: setattr(value, "type", socket.SOCK_DGRAM),
    lambda value: setattr(value, "descriptor", -1),
    lambda value: setattr(value, "settimeout", lambda timeout: None),
    lambda value: setattr(value, "local", "/tmp/client.sock"),
    lambda value: setattr(value, "peer", "/var/run/other.sock"),
))
def test_post_connect_fact_drift_closes_stream_once(mutation) -> None:
    stream = Stream()
    mutation(stream)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        connector(stream)[0].connect()
    assert stream.closed == 1


def test_non_socket_or_inheritable_descriptor_is_closed(monkeypatch) -> None:
    stream = Stream()
    monkeypatch.setattr(os, "fstat", lambda descriptor: type("F", (), {
        "st_mode": stat.S_IFREG | 0o660,
    })())
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        connector(stream)[0].connect()
    assert stream.closed == 1
    stream = Stream()
    monkeypatch.setattr(os, "fstat", lambda descriptor: Facts())
    monkeypatch.setattr(os, "get_inheritable", lambda descriptor: True)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        connector(stream)[0].connect()
    assert stream.closed == 1


def test_factory_failure_or_none_is_detail_free() -> None:
    for factory in (
        lambda family, kind: None,
        lambda family, kind: (_ for _ in ()).throw(RuntimeError("secret")),
    ):
        value = ControlledManifestHandoffSupervisorEngineApiDaemonConnector(
            daemon_socket=DAEMON, timeout_seconds=5.0, socket_factory=factory,
        )
        with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
            value.connect()
        assert "secret" not in str(caught.value)


def test_close_failure_during_error_cleanup_remains_detail_free() -> None:
    stream = Stream()
    stream.failure = "close"
    stream.peer = "/wrong.sock"
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        connector(stream)[0].connect()
    assert stream.closed == 1
    assert str(caught.value) == "manifest_handoff_registry_unavailable"


@pytest.mark.parametrize("values", (
    {"daemon_socket": Path("relative.sock"), "timeout_seconds": 1},
    {"daemon_socket": Path("/"), "timeout_seconds": 1},
    {"daemon_socket": DAEMON, "timeout_seconds": 0},
    {"daemon_socket": DAEMON, "timeout_seconds": True},
    {"daemon_socket": DAEMON, "timeout_seconds": 1, "socket_factory": object()},
))
def test_invalid_configuration_fails_without_socket_creation(values) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ControlledManifestHandoffSupervisorEngineApiDaemonConnector(**values)


def test_connector_has_no_listener_accept_shutdown_or_owned_close_surface() -> None:
    value, _ = connector(Stream())
    assert repr(value) == "ControlledManifestHandoffSupervisorEngineApiDaemonConnector()"
    for name in ("listen", "bind", "accept", "shutdown", "close"):
        assert not hasattr(value, name)
