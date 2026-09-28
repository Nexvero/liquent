import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_http11_framing import (
    ClosedManifestHandoffSupervisorEngineApiHttp11Framing,
    FramedManifestHandoffSupervisorEngineApiRequest,
    FramedManifestHandoffSupervisorEngineApiResponse,
)


FRAMING = ClosedManifestHandoffSupervisorEngineApiHttp11Framing()


def request(start, headers, body=b""):
    head = b"\r\n".join((start, *headers))
    return head + b"\r\n\r\n" + body


def response(start, headers=(), body=b""):
    head = b"\r\n".join((start, *headers))
    return head + b"\r\n\r\n" + body


def test_get_request_is_one_bodyless_http11_message() -> None:
    raw = request(b"GET /v1.45/containers/" + b"a" * 64 + b"/json HTTP/1.1", (
        b"host: localhost", b"accept: application/json",
        b"accept-encoding: identity", b"connection: close",
    ))
    assert FRAMING.decode_request(raw) == FramedManifestHandoffSupervisorEngineApiRequest(
        "GET", "/v1.45/containers/" + "a" * 64 + "/json", None, None
    )


def test_post_request_binds_exact_json_content_length() -> None:
    raw = request(b"POST /v1.45/containers/create HTTP/1.1", (
        b"host: localhost", b"accept: application/json", b"connection: close",
        b"content-type: application/json", b"content-length: 2",
    ), b"{}")
    assert FRAMING.decode_request(raw).body == b"{}"


@pytest.mark.parametrize("mutation", (
    lambda raw: raw + b"GET / HTTP/1.1\r\n\r\n",
    lambda raw: raw.replace(b"content-length: 2", b"content-length: 1"),
    lambda raw: raw.replace(b"content-length: 2", b"content-length: 02"),
    lambda raw: raw.replace(b"content-length: 2", b"transfer-encoding: chunked"),
    lambda raw: raw.replace(b"connection: close", b"connection: upgrade"),
    lambda raw: raw.replace(b"accept: application/json", b"upgrade: websocket"),
    lambda raw: raw.replace(b"host: localhost", b"host: localhost\r\nhost: localhost"),
    lambda raw: raw.replace(b"host: localhost", b"Host: localhost"),
    lambda raw: raw.replace(b"host: localhost", b"host : localhost"),
    lambda raw: raw.replace(b"HTTP/1.1", b"HTTP/1.0"),
))
def test_request_smuggling_upgrade_or_framing_extensions_fail_closed(mutation) -> None:
    raw = request(b"POST /v1.45/containers/create HTTP/1.1", (
        b"host: localhost", b"accept: application/json", b"connection: close",
        b"content-type: application/json", b"content-length: 2",
    ), b"{}")
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        FRAMING.decode_request(mutation(raw))


@pytest.mark.parametrize("status", (200, 201))
def test_json_response_preserves_status_media_type_and_body(status) -> None:
    raw = response(f"HTTP/1.1 {status} OK".encode(), (
        b"content-type: application/json", b"content-length: 2",
        b"server: Docker", b"api-version: 1.45", b"ostype: linux",
    ), b"{}")
    assert FRAMING.decode_response(raw) == FramedManifestHandoffSupervisorEngineApiResponse(
        status, "application/json", b"{}"
    )


@pytest.mark.parametrize("status", (204, 304, 404))
def test_bodyless_response_requires_no_content_headers(status) -> None:
    raw = response(f"HTTP/1.1 {status} status".encode())
    assert FRAMING.decode_response(raw).body == b""


@pytest.mark.parametrize("raw", (
    response(b"HTTP/1.1 200 OK", (b"transfer-encoding: chunked",), b"0\r\n\r\n"),
    response(b"HTTP/1.1 200 OK", (b"content-type: application/json", b"content-length: 3"), b"{}"),
    response(b"HTTP/1.1 200 OK", (b"content-type: application/json", b"content-length: 2", b"trailer: digest"), b"{}"),
    response(b"HTTP/1.0 200 OK"),
    response(b"HTTP/1.1 200 OK", (b"content-length: 0",)),
    response(b"HTTP/1.1 200 OK", (b"connection: keep-alive", b"upgrade: h2c")),
))
def test_response_chunking_trailers_mismatch_or_upgrade_fail_closed(raw) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        FRAMING.decode_response(raw)


def test_head_and_body_limits_are_closed() -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        FRAMING.decode_request(b"GET / HTTP/1.1\r\nx: " + b"a" * 16_384 + b"\r\n\r\n")
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        FRAMING.decode_response(
            b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n"
            b"content-length: 1048577\r\n\r\n" + b" " * 1_048_577
        )


def test_invalid_input_is_detail_free_and_surface_has_no_io() -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        FRAMING.decode_request(b"secret")
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "secret" not in str(caught.value)
    surface = vars(ClosedManifestHandoffSupervisorEngineApiHttp11Framing)
    for name in ("listen", "bind", "connect", "recv", "send", "close"):
        assert name not in surface
