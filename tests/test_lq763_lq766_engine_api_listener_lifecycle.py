import os
from pathlib import Path
import socket
import stat

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener import (
    ControlledManifestHandoffSupervisorEngineApiListener,
)


PATH = Path("/run/liquent/engine.sock")


class Facts:
    def __init__(self, mode, *, uid=100, gid=101, dev=7, ino=8):
        self.st_mode, self.st_uid, self.st_gid = mode, uid, gid
        self.st_dev, self.st_ino = dev, ino


class State:
    def __init__(self):
        self.exists = False
        self.mode = stat.S_IFSOCK | 0o777
        self.uid, self.gid = 0, 0
        self.dev, self.ino = 7, 8
        self.unlinks = 0


class Listener:
    family = socket.AF_UNIX
    type = socket.SOCK_STREAM

    def __init__(self, state):
        self.state = state
        self.descriptor = 19
        self.inheritable = None
        self.accepting = 0
        self.local = str(PATH)
        self.calls = []
        self.closed = 0
        self.failure = None

    def set_inheritable(self, value):
        self.calls.append(("inheritable", value))
        self.inheritable = value

    def bind(self, path):
        self.calls.append(("bind", path))
        if self.failure == "bind":
            raise RuntimeError("secret")
        self.state.exists = True

    def listen(self, backlog):
        self.calls.append(("listen", backlog))
        if self.failure == "listen":
            raise RuntimeError("secret")
        self.accepting = 1

    def fileno(self):
        return self.descriptor

    def getsockopt(self, level, option):
        return self.accepting

    def getsockname(self):
        return self.local

    def close(self):
        self.closed += 1
        if self.failure == "close":
            raise RuntimeError("close secret")


@pytest.fixture
def environment(monkeypatch):
    state = State()
    listener = Listener(state)

    def lstat(path):
        if Path(path) == PATH.parent:
            return Facts(stat.S_IFDIR | 0o700)
        if not state.exists:
            raise FileNotFoundError
        return Facts(state.mode, uid=state.uid, gid=state.gid,
                     dev=state.dev, ino=state.ino)

    monkeypatch.setattr(os, "lstat", lstat)
    monkeypatch.setattr(os, "fstat", lambda descriptor: Facts(stat.S_IFSOCK | 0o600))
    monkeypatch.setattr(os, "get_inheritable", lambda descriptor: False)
    monkeypatch.setattr(os, "chown", lambda path, uid, gid, **kwargs: (
        setattr(state, "uid", uid), setattr(state, "gid", gid)
    ))
    monkeypatch.setattr(os, "chmod", lambda path, mode, **kwargs: setattr(
        state, "mode", stat.S_IFSOCK | mode
    ))

    def unlink(path):
        state.unlinks += 1
        state.exists = False

    monkeypatch.setattr(os, "unlink", unlink)
    return state, listener


def lifecycle(listener):
    return ControlledManifestHandoffSupervisorEngineApiListener(
        socket_path=PATH, proxy_uid=100, client_gid=101,
        parent_uid=100, parent_gid=101, backlog=8,
        socket_factory=lambda family, kind: listener,
    )


def test_open_publishes_exact_private_listener_and_close_retires_it(environment) -> None:
    state, listener = environment
    value = lifecycle(listener)
    assert value.open() is listener
    assert listener.calls == [
        ("inheritable", False), ("bind", str(PATH)), ("listen", 8),
    ]
    assert (state.uid, state.gid, stat.S_IMODE(state.mode)) == (100, 101, 0o660)
    assert listener.closed == 0 and state.exists
    value.close(listener)
    assert listener.closed == 1 and not state.exists and state.unlinks == 1


def test_existing_path_is_never_bound_closed_or_removed(environment) -> None:
    state, listener = environment
    state.exists = True
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        lifecycle(listener).open()
    assert listener.calls == [] and listener.closed == 0 and state.unlinks == 0


def test_second_open_is_rejected_without_replacing_active_listener(environment) -> None:
    state, listener = environment
    value = lifecycle(listener)
    assert value.open() is listener
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        value.open()
    assert listener.closed == 0 and state.exists and state.unlinks == 0


@pytest.mark.parametrize("failure", ("bind", "listen"))
def test_open_failure_closes_and_removes_only_its_published_socket(environment, failure) -> None:
    state, listener = environment
    listener.failure = failure
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        lifecycle(listener).open()
    assert listener.closed == 1
    assert state.unlinks == (0 if failure == "bind" else 1)
    assert "secret" not in str(caught.value)


def test_replaced_path_is_not_removed_during_failed_open(environment) -> None:
    state, listener = environment

    def listen(backlog):
        state.ino = 99
        raise RuntimeError("secret")

    listener.listen = listen
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        lifecycle(listener).open()
    assert state.exists and state.unlinks == 0


def test_wrong_parent_facts_fail_before_socket_creation(environment, monkeypatch) -> None:
    state, listener = environment
    original = os.lstat

    def wrong(path):
        if Path(path) == PATH.parent:
            return Facts(stat.S_IFDIR | 0o755)
        return original(path)

    monkeypatch.setattr(os, "lstat", wrong)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        lifecycle(listener).open()
    assert listener.calls == [] and not state.exists


def test_close_wrong_listener_or_replaced_path_never_unlinks(environment) -> None:
    state, listener = environment
    value = lifecycle(listener)
    value.open()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        value.close(object())
    assert listener.closed == 0 and state.unlinks == 0
    state.ino = 99
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        value.close(listener)
    assert listener.closed == 1 and state.exists and state.unlinks == 0


def test_close_failure_keeps_active_path_for_explicit_retry(environment) -> None:
    state, listener = environment
    value = lifecycle(listener)
    value.open()
    listener.failure = "close"
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        value.close(listener)
    assert state.exists and state.unlinks == 0
    listener.failure = None
    value.close(listener)
    assert listener.closed == 2 and not state.exists


def test_lifecycle_has_no_accept_connect_or_serve_surface(environment) -> None:
    _, listener = environment
    value = lifecycle(listener)
    assert repr(value) == "ControlledManifestHandoffSupervisorEngineApiListener()"
    for name in ("accept", "connect", "serve", "run", "loop"):
        assert not hasattr(value, name)
