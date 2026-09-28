import json

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import (
    compose_manifest_handoff_supervisor_engine_api_proxy_bundle,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_protocol import (
    ClosedManifestHandoffSupervisorEngineApiHealthProtocol,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_owner import (
    ManifestHandoffSupervisorEngineApiProcessOwner,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import (
    ManifestHandoffSupervisorEngineApiProcessStatus,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import (
    ManifestHandoffSupervisorEngineApiProxySettings,
)


LIVE = b"GET /live HTTP/1.1\r\nhost: local\r\nconnection: close\r\n\r\n"
READY = b"GET /ready HTTP/1.1\r\nhost: local\r\nconnection: close\r\n\r\n"


def _settings():
    return ManifestHandoffSupervisorEngineApiProxySettings.from_mapping({
        "proxy_socket": "/run/liquent/engine.sock", "daemon_socket": "/var/run/docker.sock",
        "control_root": "/srv/liquent/control", "source_root": "/srv/liquent/source",
        "target_root": "/srv/liquent/target", "writer_command": "/opt/liquent/writer",
        "recovery_command": "/opt/liquent/recovery", "proxy_uid": "10001",
        "client_gid": "10002", "daemon_uid": "0", "daemon_gid": "998",
        "host_owner_uid": "10003", "host_owner_gid": "10004",
        "data_owner_uid": "10005", "data_gid": "10006", "wrapper_uid": "10007",
        "wrapper_gid": "10008", "client_timeout_seconds": "15",
        "daemon_timeout_seconds": "30", "listener_backlog": "16",
        "maximum_exchanges": "10000",
    })


def _protocol():
    bundle = compose_manifest_handoff_supervisor_engine_api_proxy_bundle(_settings())
    owner = ManifestHandoffSupervisorEngineApiProcessOwner(bundle)
    return ClosedManifestHandoffSupervisorEngineApiHealthProtocol(owner), bundle.status


def _decode(response):
    head, body = response.split(b"\r\n\r\n", 1)
    length = int([
        line for line in head.split(b"\r\n")
        if line.startswith(b"content-length: ")
    ][0].split(b": ", 1)[1])
    assert length == len(body) <= 256
    assert b"connection: close" in head
    assert b"content-type: application/json" in head
    return head.split(b"\r\n", 1)[0], json.loads(body)


def test_initial_is_live_but_not_ready_with_fixed_reasons() -> None:
    protocol, status = _protocol()
    assert _decode(protocol.handle(LIVE)) == (
        b"HTTP/1.1 200 OK",
        {"live": True, "reason": "manifest_handoff_supervisor_engine_api_initial"},
    )
    assert _decode(protocol.handle(READY)) == (
        b"HTTP/1.1 503 Service Unavailable",
        {"ready": False, "reason": "manifest_handoff_supervisor_engine_api_initial"},
    )


def test_serving_is_live_and_ready_then_stopping_is_not_ready() -> None:
    protocol, status = _protocol()
    status.mark_starting()
    status.mark_serving()
    assert _decode(protocol.handle(LIVE))[0] == b"HTTP/1.1 200 OK"
    assert _decode(protocol.handle(READY)) == (
        b"HTTP/1.1 200 OK",
        {"ready": True, "reason": "manifest_handoff_supervisor_engine_api_ready"},
    )
    status.mark_stopping()
    code, body = _decode(protocol.handle(READY))
    assert code == b"HTTP/1.1 503 Service Unavailable"
    assert body == {
        "ready": False,
        "reason": "manifest_handoff_supervisor_engine_api_stopping",
    }


@pytest.mark.parametrize("terminal", ("stopped", "failed"))
def test_terminal_state_is_neither_live_nor_ready(terminal) -> None:
    protocol, status = _protocol()
    if terminal == "stopped":
        status.mark_starting(); status.mark_stopping(); status.mark_stopped()
    else:
        status.mark_failed()
    for request, field in ((LIVE, "live"), (READY, "ready")):
        code, body = _decode(protocol.handle(request))
        assert code == b"HTTP/1.1 503 Service Unavailable"
        assert body[field] is False
        assert set(body) == {field, "reason"}


@pytest.mark.parametrize("message", (
    b"", b"GET /unknown HTTP/1.1\r\nhost: local\r\nconnection: close\r\n\r\n",
    b"POST /live HTTP/1.1\r\nhost: local\r\nconnection: close\r\n\r\n",
    b"GET /live HTTP/1.1\r\nHost: local\r\nconnection: close\r\n\r\n",
    b"GET /live HTTP/1.1\r\nhost: other\r\nconnection: close\r\n\r\n",
    LIVE + b"body", b"x" * 129,
))
def test_unknown_mutating_noncanonical_or_oversized_request_fails_closed(message) -> None:
    protocol, status = _protocol()
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        protocol.handle(message)
    assert status.snapshot().phase.value == "initial"


def test_live_technical_failure_becomes_detail_free_503(monkeypatch) -> None:
    protocol, status = _protocol()
    monkeypatch.setattr(
        ManifestHandoffSupervisorEngineApiProcessStatus, "snapshot",
        lambda self: (_ for _ in ()).throw(RuntimeError("private path detail")),
    )
    code, body = _decode(protocol.handle(LIVE))
    assert code == b"HTTP/1.1 503 Service Unavailable"
    assert body == {
        "live": False,
        "reason": "manifest_handoff_supervisor_engine_api_unavailable",
    }


def test_protocol_accepts_only_exact_owner_and_has_no_io_surface() -> None:
    for value in (None, object(), "owner"):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            ClosedManifestHandoffSupervisorEngineApiHealthProtocol(value)
    protocol, status = _protocol()
    assert repr(protocol) == "ClosedManifestHandoffSupervisorEngineApiHealthProtocol()"
    for name in ("listen", "accept", "connect", "close", "run", "serve"):
        assert not hasattr(protocol, name)
