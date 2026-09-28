from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import (
    AuthorizedManifestHandoffSupervisorEngineApiClientPeer,
    LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_exchange import (
    VerifiedManifestHandoffSupervisorEngineApiHealthExchange,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_protocol import (
    ClosedManifestHandoffSupervisorEngineApiHealthProtocol,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_stream_io import (
    BoundedManifestHandoffSupervisorEngineApiHealthStreamIo,
)


REQUEST = b"GET /live HTTP/1.1\r\nhost: local\r\nconnection: close\r\n\r\n"
RESPONSE = b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n"


class Stream:
    def __init__(self):
        self.descriptor = 17
        self.closed = 0

    def fileno(self):
        return self.descriptor

    def close(self):
        self.closed += 1


def objects():
    return (
        object.__new__(LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy),
        object.__new__(ClosedManifestHandoffSupervisorEngineApiHealthProtocol),
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo(),
    )


def token(stream, descriptor=None):
    return AuthorizedManifestHandoffSupervisorEngineApiClientPeer(
        stream.descriptor if descriptor is None else descriptor,
        123, 10001, 10002, Path("/run/liquent/health.sock"), stream,
    )


def test_verify_read_handle_write_exact_order_without_close(monkeypatch) -> None:
    peer, protocol, io = objects()
    stream, calls = Stream(), []
    monkeypatch.setattr(
        LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy, "authorize",
        lambda self, current: calls.append(("verify", current)) or token(current),
    )
    monkeypatch.setattr(
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo, "read_request",
        lambda self, current: calls.append(("read", current)) or REQUEST,
    )
    monkeypatch.setattr(
        ClosedManifestHandoffSupervisorEngineApiHealthProtocol, "handle",
        lambda self, message: calls.append(("handle", message)) or RESPONSE,
    )
    monkeypatch.setattr(
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo, "write_response",
        lambda self, current, message: calls.append(("write", current, message)),
    )
    VerifiedManifestHandoffSupervisorEngineApiHealthExchange(
        peer, protocol, stream_io=io
    ).exchange(stream)
    assert [call[0] for call in calls] == ["verify", "read", "handle", "write"]
    assert calls[0][1] is calls[1][1] is calls[3][1] is stream
    assert calls[2][1] is REQUEST and calls[3][2] is RESPONSE
    assert stream.closed == 0


@pytest.mark.parametrize("stage", ("verify", "read", "handle", "write"))
def test_each_stage_failure_stops_later_effects_and_is_detail_free(monkeypatch, stage) -> None:
    peer, protocol, io = objects()
    stream, calls = Stream(), []

    def step(name, value=None):
        calls.append(name)
        if stage == name:
            raise RuntimeError(f"private {name} detail")
        return value

    monkeypatch.setattr(
        LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy, "authorize",
        lambda self, current: step("verify", token(current)),
    )
    monkeypatch.setattr(
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo, "read_request",
        lambda self, current: step("read", REQUEST),
    )
    monkeypatch.setattr(
        ClosedManifestHandoffSupervisorEngineApiHealthProtocol, "handle",
        lambda self, message: step("handle", RESPONSE),
    )
    monkeypatch.setattr(
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo, "write_response",
        lambda self, current, message: step("write"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        VerifiedManifestHandoffSupervisorEngineApiHealthExchange(
            peer, protocol, stream_io=io
        ).exchange(stream)
    expected = ["verify", "read", "handle", "write"]
    assert calls == expected[:expected.index(stage) + 1]
    assert "private" not in str(caught.value)
    assert stream.closed == 0


def test_foreign_token_stream_or_descriptor_fails_before_read(monkeypatch) -> None:
    peer, protocol, io = objects()
    stream, foreign, reads = Stream(), Stream(), []
    foreign.descriptor = stream.descriptor
    for authorized in (object(), token(foreign), token(stream, descriptor=18)):
        monkeypatch.setattr(
            LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy, "authorize",
            lambda self, current, value=authorized: value,
        )
        monkeypatch.setattr(
            BoundedManifestHandoffSupervisorEngineApiHealthStreamIo, "read_request",
            lambda *args: reads.append("read"),
        )
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            VerifiedManifestHandoffSupervisorEngineApiHealthExchange(
                peer, protocol, stream_io=io
            ).exchange(stream)
    assert reads == []


def test_descriptor_change_after_protocol_fails_before_write(monkeypatch) -> None:
    peer, protocol, io = objects()
    stream, writes = Stream(), []
    monkeypatch.setattr(
        LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy, "authorize",
        lambda self, current: token(current),
    )
    monkeypatch.setattr(
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo, "read_request",
        lambda self, current: REQUEST,
    )

    def handle(self, message):
        stream.descriptor = 18
        return RESPONSE

    monkeypatch.setattr(ClosedManifestHandoffSupervisorEngineApiHealthProtocol, "handle", handle)
    monkeypatch.setattr(
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo, "write_response",
        lambda *args: writes.append("write"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        VerifiedManifestHandoffSupervisorEngineApiHealthExchange(
            peer, protocol, stream_io=io
        ).exchange(stream)
    assert writes == []


@pytest.mark.parametrize("values", (
    (object(), object.__new__(ClosedManifestHandoffSupervisorEngineApiHealthProtocol), None),
    (object.__new__(LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy), object(), None),
    (object.__new__(LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy), object.__new__(ClosedManifestHandoffSupervisorEngineApiHealthProtocol), object()),
))
def test_only_exact_dependencies_can_be_composed(values) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        VerifiedManifestHandoffSupervisorEngineApiHealthExchange(
            values[0], values[1], stream_io=values[2]
        )


def test_exchange_has_no_acquire_close_listener_or_loop_surface() -> None:
    peer, protocol, io = objects()
    value = VerifiedManifestHandoffSupervisorEngineApiHealthExchange(
        peer, protocol, stream_io=io
    )
    assert repr(value) == "VerifiedManifestHandoffSupervisorEngineApiHealthExchange()"
    for name in ("open", "close", "connect", "listen", "accept", "run", "serve"):
        assert not hasattr(value, name)
