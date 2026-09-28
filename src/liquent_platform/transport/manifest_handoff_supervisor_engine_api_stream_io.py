"""Bounded single-message stream I/O for the future Engine API proxy."""

from __future__ import annotations

from typing import Protocol

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_MAX_HEAD_BYTES = 16_384
_MAX_BODY_BYTES = 1_048_576
_MAX_MESSAGE_BYTES = _MAX_HEAD_BYTES + _MAX_BODY_BYTES
_READ_BYTES = 4_096


class _ReadableStream(Protocol):
    def recv(self, maximum: int) -> bytes: ...


class _WritableStream(Protocol):
    def send(self, data: memoryview) -> int: ...


class BoundedManifestHandoffSupervisorEngineApiStreamIo:
    """Read or write exactly one bounded message on an owned-elsewhere stream."""

    def read(self, stream: _ReadableStream) -> bytes:
        try:
            if stream is None or not callable(getattr(stream, "recv", None)):
                raise ManifestHandoffRegistryUnavailable
            collected = bytearray()
            boundary = -1
            while boundary < 0:
                remaining = _MAX_HEAD_BYTES - len(collected)
                if remaining < 1:
                    raise ManifestHandoffRegistryUnavailable
                chunk = self._recv(stream, min(_READ_BYTES, remaining))
                collected.extend(chunk)
                boundary = collected.find(b"\r\n\r\n")
            head_end = boundary + 4
            if head_end > _MAX_HEAD_BYTES:
                raise ManifestHandoffRegistryUnavailable
            body_bytes = self._content_length(bytes(collected[:boundary]))
            expected = head_end + body_bytes
            if expected > _MAX_MESSAGE_BYTES or len(collected) > expected:
                raise ManifestHandoffRegistryUnavailable
            while len(collected) < expected:
                chunk = self._recv(
                    stream, min(_READ_BYTES, expected - len(collected))
                )
                collected.extend(chunk)
            if len(collected) != expected:
                raise ManifestHandoffRegistryUnavailable
            return bytes(collected)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def write(self, stream: _WritableStream, message: bytes) -> None:
        try:
            if (
                stream is None
                or not callable(getattr(stream, "send", None))
                or type(message) is not bytes
                or not message
                or len(message) > _MAX_MESSAGE_BYTES
            ):
                raise ManifestHandoffRegistryUnavailable
            boundary = message.find(b"\r\n\r\n")
            if boundary < 1 or boundary + 4 > _MAX_HEAD_BYTES:
                raise ManifestHandoffRegistryUnavailable
            view = memoryview(message)
            sent = 0
            while sent < len(view):
                current = stream.send(view[sent:])
                if type(current) is not int or current < 1 or current > len(view) - sent:
                    raise ManifestHandoffRegistryUnavailable
                sent += current
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _recv(stream, maximum):
        value = stream.recv(maximum)
        if type(value) is not bytes or not value or len(value) > maximum:
            raise ManifestHandoffRegistryUnavailable
        return value

    @staticmethod
    def _content_length(head):
        lines = head.split(b"\r\n")
        declared = []
        for line in lines[1:]:
            if line.lower().startswith(b"content-length:"):
                if not line.startswith(b"content-length: "):
                    raise ManifestHandoffRegistryUnavailable
                declared.append(line[len(b"content-length: "):])
            if line.lower().startswith(b"transfer-encoding:"):
                raise ManifestHandoffRegistryUnavailable
        if not declared:
            return 0
        if len(declared) != 1:
            raise ManifestHandoffRegistryUnavailable
        value = declared[0]
        if (
            not value
            or not value.isdigit()
            or (len(value) > 1 and value.startswith(b"0"))
            or int(value) > _MAX_BODY_BYTES
        ):
            raise ManifestHandoffRegistryUnavailable
        return int(value)
