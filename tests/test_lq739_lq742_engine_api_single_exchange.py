from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_exchange import (
    ClosedManifestHandoffSupervisorEngineApiExchange,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_gate import (
    ClosedManifestHandoffSupervisorEngineApiGate,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import (
    ClosedManifestHandoffSupervisorCreateRequestPolicy,
)


CONTAINER = "a" * 64


class Stream:
    def __init__(self, incoming=(), send_limit=None):
        self.incoming = list(incoming)
        self.sent = bytearray()
        self.send_limit = send_limit
        self.closed = 0

    def recv(self, maximum):
        if not self.incoming:
            return b""
        value = self.incoming.pop(0)
        if len(value) > maximum:
            self.incoming.insert(0, value[maximum:])
            value = value[:maximum]
        return value

    def send(self, value):
        size = len(value) if self.send_limit is None else min(self.send_limit, len(value))
        self.sent.extend(value[:size])
        return size

    def close(self):
        self.closed += 1


def request(target=None):
    target = target or f"/v1.45/containers/{CONTAINER}/json"
    return (
        f"GET {target} HTTP/1.1\r\n".encode()
        + b"host: localhost\r\naccept: application/json\r\n"
        + b"connection: close\r\n\r\n"
    )


def response(status, body=None):
    reason = {200: "OK", 404: "Not Found", 500: "Error"}[status]
    start = f"HTTP/1.1 {status} {reason}\r\n".encode()
    if body is None:
        return start + b"\r\n"
    return (
        start + b"content-type: application/json\r\n"
        + f"content-length: {len(body)}\r\n\r\n".encode() + body
    )


def exchange():
    create = ClosedManifestHandoffSupervisorCreateRequestPolicy(
        control_root=Path("/srv/liquent/control"),
        source_root=Path("/srv/liquent/source"),
        target_root=Path("/srv/liquent/target"),
        writer_command="writer-wrapper", recovery_command="recovery-wrapper",
        wrapper_uid=10002, wrapper_gid=10003,
    )
    return ClosedManifestHandoffSupervisorEngineApiExchange(
        ClosedManifestHandoffSupervisorEngineApiGate(create)
    )


def test_valid_exchange_forwards_request_then_canonical_response() -> None:
    original = request()
    client = Stream((original[:19], original[19:]), send_limit=5)
    daemon = Stream((response(200, b'{"Id":"a"}'),), send_limit=7)
    exchange().exchange(client, daemon)
    assert bytes(daemon.sent) == original
    assert bytes(client.sent) == (
        b"HTTP/1.1 200 OK\r\nconnection: close\r\n"
        b"content-type: application/json\r\ncontent-length: 10\r\n\r\n"
        b'{"Id":"a"}'
    )
    assert client.closed == daemon.closed == 0


def test_neutral_absence_is_serialized_without_daemon_detail_or_media_type() -> None:
    client, daemon = Stream((request(),)), Stream((response(404),))
    exchange().exchange(client, daemon)
    assert bytes(client.sent) == (
        b"HTTP/1.1 404 Not Found\r\nconnection: close\r\n\r\n"
    )


def test_rejected_request_never_reaches_daemon() -> None:
    client = Stream((request("/v1.45/images/json"),))
    daemon = Stream((response(200, b"[]"),))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        exchange().exchange(client, daemon)
    assert bytes(daemon.sent) == b""
    assert bytes(client.sent) == b""


def test_rejected_daemon_response_never_reaches_client() -> None:
    client = Stream((request(),))
    daemon = Stream((response(500, b'{"message":"secret"}'),))
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        exchange().exchange(client, daemon)
    assert bytes(daemon.sent) == request()
    assert bytes(client.sent) == b""
    assert "secret" not in str(caught.value)


def test_truncated_daemon_response_never_reaches_client() -> None:
    raw = b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: 3\r\n\r\n{}"
    client, daemon = Stream((request(),)), Stream((raw,))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        exchange().exchange(client, daemon)
    assert bytes(client.sent) == b""


def test_same_stream_is_rejected_before_any_io() -> None:
    stream = Stream((request(), response(404)))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        exchange().exchange(stream, stream)
    assert stream.incoming == [request(), response(404)]
    assert bytes(stream.sent) == b""


def test_invalid_stream_or_write_progress_fails_detail_free() -> None:
    class Broken(Stream):
        def send(self, value):
            raise RuntimeError("secret")

    client, daemon = Stream((request(),)), Broken((response(404),))
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        exchange().exchange(client, daemon)
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "secret" not in str(caught.value)


def test_exchange_has_no_listener_connect_timeout_or_close_surface() -> None:
    value = exchange()
    assert repr(value) == "ClosedManifestHandoffSupervisorEngineApiExchange()"
    for name in ("listen", "bind", "accept", "connect", "settimeout", "close"):
        assert not hasattr(value, name)
