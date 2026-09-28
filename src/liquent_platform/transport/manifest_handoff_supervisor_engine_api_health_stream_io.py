"""Bounded single-message stream I/O for local Engine API proxy health."""

from __future__ import annotations

from typing import Protocol

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_MAXIMUM_REQUEST_BYTES = 128
_MAXIMUM_RESPONSE_BYTES = 512
_READ_BYTES = 64


class _ReadableStream(Protocol):
    def recv(self, maximum: int) -> bytes: ...


class _WritableStream(Protocol):
    def send(self, data: memoryview) -> int: ...


class BoundedManifestHandoffSupervisorEngineApiHealthStreamIo:
    """Read one header-only request and write one bounded response."""

    def __repr__(self) -> str:
        return "BoundedManifestHandoffSupervisorEngineApiHealthStreamIo()"

    def read_request(self, stream: _ReadableStream) -> bytes:
        try:
            if stream is None or not callable(getattr(stream, "recv", None)):
                raise ManifestHandoffRegistryUnavailable
            collected = bytearray()
            while True:
                remaining = _MAXIMUM_REQUEST_BYTES - len(collected)
                if remaining < 1:
                    raise ManifestHandoffRegistryUnavailable
                chunk = stream.recv(min(_READ_BYTES, remaining))
                if type(chunk) is not bytes or not chunk or len(chunk) > min(
                    _READ_BYTES, remaining
                ):
                    raise ManifestHandoffRegistryUnavailable
                collected.extend(chunk)
                boundary = collected.find(b"\r\n\r\n")
                if boundary >= 0:
                    if boundary + 4 != len(collected):
                        raise ManifestHandoffRegistryUnavailable
                    return bytes(collected)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def write_response(self, stream: _WritableStream, response: bytes) -> None:
        try:
            if (
                stream is None
                or not callable(getattr(stream, "send", None))
                or type(response) is not bytes
                or not response
                or len(response) > _MAXIMUM_RESPONSE_BYTES
                or response.find(b"\r\n\r\n") < 1
            ):
                raise ManifestHandoffRegistryUnavailable
            view = memoryview(response)
            sent = 0
            while sent < len(view):
                current = stream.send(view[sent:])
                if (
                    type(current) is not int
                    or current < 1
                    or current > len(view) - sent
                ):
                    raise ManifestHandoffRegistryUnavailable
                sent += current
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
