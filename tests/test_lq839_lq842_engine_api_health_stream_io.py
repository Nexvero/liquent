import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_stream_io import (
    BoundedManifestHandoffSupervisorEngineApiHealthStreamIo,
)


REQUEST = b"GET /live HTTP/1.1\r\nhost: local\r\nconnection: close\r\n\r\n"
RESPONSE = (
    b"HTTP/1.1 200 OK\r\nconnection: close\r\n"
    b"content-type: application/json\r\ncontent-length: 13\r\n\r\n"
    b'{"live":true}'
)


class Reader:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.maximums = []

    def recv(self, maximum):
        self.maximums.append(maximum)
        if not self.chunks:
            return b""
        value = self.chunks.pop(0)
        if len(value) > maximum:
            head, tail = value[:maximum], value[maximum:]
            self.chunks.insert(0, tail)
            return head
        return value


class Writer:
    def __init__(self, maximum=10_000, result=None):
        self.maximum = maximum
        self.result = result
        self.content = bytearray()

    def send(self, data):
        if self.result is not None:
            return self.result
        count = min(self.maximum, len(data))
        self.content.extend(data[:count])
        return count


def test_fragmented_request_is_read_once_to_exact_boundary() -> None:
    reader = Reader((REQUEST[:7], REQUEST[7:31], REQUEST[31:]))
    result = BoundedManifestHandoffSupervisorEngineApiHealthStreamIo().read_request(reader)
    assert result == REQUEST
    assert all(1 <= value <= 64 for value in reader.maximums)
    assert reader.chunks == []


def test_complete_request_in_one_chunk_is_returned_without_another_read() -> None:
    reader = Reader((REQUEST, b"unread"))
    assert BoundedManifestHandoffSupervisorEngineApiHealthStreamIo().read_request(reader) == REQUEST
    assert reader.chunks == [b"unread"]


@pytest.mark.parametrize("chunks", (
    (), (b"",), (b"GET /live", b""),
    (REQUEST + b"body",), (b"x" * 128,),
))
def test_eof_extra_bytes_or_missing_boundary_fails_closed(chunks) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo().read_request(
            Reader(chunks)
        )


def test_response_is_fully_written_across_partial_sends() -> None:
    writer = Writer(maximum=7)
    BoundedManifestHandoffSupervisorEngineApiHealthStreamIo().write_response(
        writer, RESPONSE
    )
    assert bytes(writer.content) == RESPONSE


@pytest.mark.parametrize("response", (
    b"", b"no-boundary", b"x" * 513, bytearray(RESPONSE),
))
def test_empty_unframed_oversized_or_nonbytes_response_fails_closed(response) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo().write_response(
            Writer(), response
        )


@pytest.mark.parametrize("result", (0, -1, True, 10_000, None))
def test_invalid_send_result_or_stream_fails_closed(result) -> None:
    stream = None if result is None else Writer(result=result)
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        BoundedManifestHandoffSupervisorEngineApiHealthStreamIo().write_response(
            stream, RESPONSE
        )


def test_io_has_no_close_connect_listener_protocol_or_owner_surface() -> None:
    value = BoundedManifestHandoffSupervisorEngineApiHealthStreamIo()
    assert repr(value) == "BoundedManifestHandoffSupervisorEngineApiHealthStreamIo()"
    for name in ("close", "connect", "listen", "accept", "handle", "owner"):
        assert not hasattr(value, name)
