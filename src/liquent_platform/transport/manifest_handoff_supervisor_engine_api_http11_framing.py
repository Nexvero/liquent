"""Strict single-message HTTP/1.1 framing for the future Engine API proxy."""

from __future__ import annotations

from dataclasses import dataclass
import re

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_MAX_HEAD_BYTES = 16_384
_MAX_BODY_BYTES = 1_048_576
_TOKEN = re.compile(rb"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_TARGET = re.compile(rb"^[\x21-\x7e]{1,4096}$")
_STATUS = re.compile(rb"^HTTP/1\.1 ([0-9]{3})(?: [\x20-\x7e]{0,128})?$")
_RESPONSE_METADATA = frozenset((
    b"api-version", b"connection", b"date", b"docker-experimental",
    b"ostype", b"server",
))


@dataclass(frozen=True, slots=True)
class FramedManifestHandoffSupervisorEngineApiRequest:
    method: str
    target: str
    content_type: str | None
    body: bytes | None


@dataclass(frozen=True, slots=True)
class FramedManifestHandoffSupervisorEngineApiResponse:
    status: int
    content_type: str | None
    body: bytes


class ClosedManifestHandoffSupervisorEngineApiHttp11Framing:
    """Decode exactly one non-chunked HTTP/1.1 request or response."""

    def decode_request(
        self, message: bytes
    ) -> FramedManifestHandoffSupervisorEngineApiRequest:
        try:
            start, headers, body = self._message(message)
            parts = start.split(b" ")
            if (
                len(parts) != 3
                or parts[0] not in {b"GET", b"POST"}
                or not _TARGET.fullmatch(parts[1])
                or parts[2] != b"HTTP/1.1"
            ):
                raise ManifestHandoffRegistryUnavailable
            allowed = {
                b"host", b"accept", b"accept-encoding", b"connection",
                b"content-type", b"content-length",
            }
            if set(headers) - allowed:
                raise ManifestHandoffRegistryUnavailable
            if (
                headers.get(b"host") != b"localhost"
                or headers.get(b"accept") != b"application/json"
                or headers.get(b"connection") != b"close"
                or headers.get(b"accept-encoding", b"identity") != b"identity"
            ):
                raise ManifestHandoffRegistryUnavailable
            framed_body, content_type = self._body(headers, body, request=True)
            return FramedManifestHandoffSupervisorEngineApiRequest(
                parts[0].decode("ascii"), parts[1].decode("ascii"),
                content_type, framed_body,
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def decode_response(
        self, message: bytes
    ) -> FramedManifestHandoffSupervisorEngineApiResponse:
        try:
            start, headers, body = self._message(message)
            matched = _STATUS.fullmatch(start)
            if matched is None or set(headers) - (
                _RESPONSE_METADATA | {b"content-type", b"content-length"}
            ):
                raise ManifestHandoffRegistryUnavailable
            framed_body, content_type = self._body(headers, body, request=False)
            return FramedManifestHandoffSupervisorEngineApiResponse(
                int(matched.group(1)), content_type, framed_body,
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _message(message: bytes) -> tuple[bytes, dict[bytes, bytes], bytes]:
        if type(message) is not bytes or not message:
            raise ManifestHandoffRegistryUnavailable
        boundary = message.find(b"\r\n\r\n")
        if boundary < 1 or boundary + 4 > _MAX_HEAD_BYTES:
            raise ManifestHandoffRegistryUnavailable
        head, body = message[:boundary], message[boundary + 4:]
        if len(body) > _MAX_BODY_BYTES or b"\x00" in head:
            raise ManifestHandoffRegistryUnavailable
        lines = head.split(b"\r\n")
        if not lines or any(b"\r" in line or b"\n" in line for line in lines):
            raise ManifestHandoffRegistryUnavailable
        headers = {}
        for line in lines[1:]:
            if b":" not in line or line[:1] in b" \t":
                raise ManifestHandoffRegistryUnavailable
            name, value = line.split(b":", 1)
            normalized = name.lower()
            if (
                not _TOKEN.fullmatch(name)
                or name != normalized
                or normalized in headers
                or not value.startswith(b" ")
                or value != b" " + value[1:].strip(b" \t")
                or any(item < 0x20 or item > 0x7e for item in value[1:])
            ):
                raise ManifestHandoffRegistryUnavailable
            headers[normalized] = value[1:]
        return lines[0], headers, body

    @staticmethod
    def _body(headers, body, *, request):
        declared = headers.get(b"content-length")
        content_type = headers.get(b"content-type")
        if declared is None:
            if body or content_type is not None:
                raise ManifestHandoffRegistryUnavailable
            return (None if request else b""), None
        if (
            not declared
            or not declared.isdigit()
            or (len(declared) > 1 and declared.startswith(b"0"))
            or int(declared) != len(body)
            or len(body) > _MAX_BODY_BYTES
            or content_type != b"application/json"
        ):
            raise ManifestHandoffRegistryUnavailable
        return body, "application/json"
