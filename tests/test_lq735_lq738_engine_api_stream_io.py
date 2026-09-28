import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stream_io import (
    BoundedManifestHandoffSupervisorEngineApiStreamIo,
)


IO = BoundedManifestHandoffSupervisorEngineApiStreamIo()


class Stream:
    def __init__(self, incoming=(), send_limit=None):
        self.incoming = list(incoming)
        self.requests = []
        self.sent = bytearray()
        self.send_limit = send_limit
        self.closed = 0

    def recv(self, maximum):
        self.requests.append(maximum)
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


def message(body=b""):
    headers = b"content-type: application/json\r\ncontent-length: " + str(len(body)).encode()
    return b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n\r\n" + body


def test_fragmented_header_and_body_are_read_exactly_once() -> None:
    expected = message(b'{"value":1}')
    stream = Stream((expected[:7], expected[7:31], expected[31:55], expected[55:]))
    assert IO.read(stream) == expected
    assert not stream.incoming
    assert stream.closed == 0


def test_reader_never_requests_beyond_the_declared_remainder() -> None:
    expected = message(b"{}")
    stream = Stream((expected[:-1], expected[-1:] + b"pipelined"))
    assert IO.read(stream) == expected
    assert stream.requests[-1] == 1
    assert stream.incoming == [b"pipelined"]


def test_bodyless_message_stops_at_header_boundary() -> None:
    expected = b"HTTP/1.1 204 status\r\n\r\n"
    assert IO.read(Stream((expected,))) == expected


@pytest.mark.parametrize("incoming", (
    (b"HTTP/1.1 200 OK\r\ncontent-length: 2\r\n\r\n{}extra",),
    (b"HTTP/1.1 200 OK\r\ncontent-length: 2\r\ncontent-length: 2\r\n\r\n{}",),
    (b"HTTP/1.1 200 OK\r\ncontent-length: 02\r\n\r\n{}",),
    (b"HTTP/1.1 200 OK\r\ntransfer-encoding: chunked\r\n\r\n",),
    (b"HTTP/1.1 200 OK\r\ncontent-length: 3\r\n\r\n{}",),
    (b"HTTP/1.1 200 OK\r\ncontent-length: 1048577\r\n\r\n",),
))
def test_overread_duplicate_length_chunking_truncation_or_overlimit_fail_closed(
    incoming,
) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        IO.read(Stream(incoming))


def test_oversized_unterminated_header_is_bounded() -> None:
    stream = Stream((b"x" * 20_000,))
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        IO.read(stream)
    assert sum(stream.requests) <= 16_384


def test_partial_writes_are_completed_without_closing_stream() -> None:
    expected = message(b"{}")
    stream = Stream(send_limit=3)
    IO.write(stream, expected)
    assert bytes(stream.sent) == expected
    assert stream.closed == 0


@pytest.mark.parametrize("result", (0, -1, True, "1"))
def test_invalid_send_progress_fails_closed(result) -> None:
    class Invalid:
        def send(self, value):
            return result

    with pytest.raises(ManifestHandoffRegistryUnavailable):
        IO.write(Invalid(), message(b"{}"))


def test_stream_exceptions_and_invalid_interfaces_are_detail_free() -> None:
    class Broken:
        def recv(self, maximum):
            raise RuntimeError("secret")

    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        IO.read(Broken())
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "secret" not in str(caught.value)
    for value in (None, object()):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            IO.read(value)
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            IO.write(value, message(b"{}"))


def test_io_has_no_listener_connect_timeout_or_close_surface() -> None:
    surface = vars(BoundedManifestHandoffSupervisorEngineApiStreamIo)
    for name in ("listen", "bind", "accept", "connect", "settimeout", "close"):
        assert name not in surface
