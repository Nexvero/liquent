from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_connected_exchange import ConnectedManifestHandoffSupervisorEngineApiExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_connector import ControlledManifestHandoffSupervisorEngineApiDaemonConnector
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_peer import LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_exchange import ClosedManifestHandoffSupervisorEngineApiExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_gate import ClosedManifestHandoffSupervisorEngineApiGate
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import ClosedManifestHandoffSupervisorCreateRequestPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_verified_exchange import VerifiedManifestHandoffSupervisorEngineApiExchange


CLIENT = Path("/run/liquent/engine.sock")
DAEMON = Path("/var/run/docker.sock")


class Stream:
    def __init__(self, *, close_failure=False):
        self.closed = 0
        self.close_failure = close_failure

    def close(self):
        self.closed += 1
        if self.close_failure:
            raise RuntimeError("close secret")


def dependencies():
    connector = ControlledManifestHandoffSupervisorEngineApiDaemonConnector(
        daemon_socket=DAEMON, timeout_seconds=5.0,
        socket_factory=lambda family, kind: None,
    )
    create = ClosedManifestHandoffSupervisorCreateRequestPolicy(
        control_root=Path("/srv/liquent/control"),
        source_root=Path("/srv/liquent/source"),
        target_root=Path("/srv/liquent/target"),
        writer_command="writer-wrapper", recovery_command="recovery-wrapper",
        wrapper_uid=10002, wrapper_gid=10003,
    )
    verified = VerifiedManifestHandoffSupervisorEngineApiExchange(
        LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy(
            local_socket=CLIENT, client_uid=10001, client_gid=10002,
            timeout_seconds=5.0,
        ),
        LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy(
            daemon_socket=DAEMON, daemon_uid=0, daemon_gid=998,
            timeout_seconds=5.0,
        ),
        ClosedManifestHandoffSupervisorEngineApiExchange(
            ClosedManifestHandoffSupervisorEngineApiGate(create)
        ),
    )
    return connector, verified


def operation():
    return ConnectedManifestHandoffSupervisorEngineApiExchange(*dependencies())


def test_connect_verify_exchange_then_close_exactly_once(monkeypatch) -> None:
    client, daemon = Stream(), Stream()
    calls = []
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiDaemonConnector,
        "connect", lambda self: calls.append("connect") or daemon,
    )
    monkeypatch.setattr(
        VerifiedManifestHandoffSupervisorEngineApiExchange,
        "exchange", lambda self, left, right: calls.append(("exchange", left, right)),
    )
    operation().serve(client)
    assert calls == ["connect", ("exchange", client, daemon)]
    assert daemon.closed == 1
    assert client.closed == 0


def test_connect_failure_has_no_close_target_or_exchange(monkeypatch) -> None:
    client = Stream()
    calls = []

    def fail(self):
        calls.append("connect")
        raise RuntimeError("connect secret")

    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiDaemonConnector, "connect", fail)
    monkeypatch.setattr(
        VerifiedManifestHandoffSupervisorEngineApiExchange,
        "exchange", lambda *args: calls.append("exchange"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().serve(client)
    assert calls == ["connect"]
    assert client.closed == 0
    assert "secret" not in str(caught.value)


def test_exchange_failure_still_closes_daemon_once(monkeypatch) -> None:
    client, daemon = Stream(), Stream()
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiDaemonConnector,
        "connect", lambda self: daemon,
    )
    monkeypatch.setattr(
        VerifiedManifestHandoffSupervisorEngineApiExchange,
        "exchange", lambda *args: (_ for _ in ()).throw(RuntimeError("exchange secret")),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().serve(client)
    assert daemon.closed == 1 and client.closed == 0
    assert "secret" not in str(caught.value)


def test_close_failure_after_success_is_technical_unavailability(monkeypatch) -> None:
    client, daemon = Stream(), Stream(close_failure=True)
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiDaemonConnector,
        "connect", lambda self: daemon,
    )
    monkeypatch.setattr(
        VerifiedManifestHandoffSupervisorEngineApiExchange,
        "exchange", lambda *args: None,
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().serve(client)
    assert daemon.closed == 1 and client.closed == 0
    assert "secret" not in str(caught.value)


def test_exchange_and_close_failure_remain_one_detail_free_failure(monkeypatch) -> None:
    client, daemon = Stream(), Stream(close_failure=True)
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiDaemonConnector,
        "connect", lambda self: daemon,
    )
    monkeypatch.setattr(
        VerifiedManifestHandoffSupervisorEngineApiExchange,
        "exchange", lambda *args: (_ for _ in ()).throw(RuntimeError("exchange secret")),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        operation().serve(client)
    assert daemon.closed == 1
    assert str(caught.value) == "manifest_handoff_registry_unavailable"


@pytest.mark.parametrize("first,second", (
    (object(), dependencies()[1]),
    (dependencies()[0], object()),
))
def test_only_concrete_connector_and_verified_exchange_can_be_composed(first, second) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ConnectedManifestHandoffSupervisorEngineApiExchange(first, second)


def test_operation_has_no_listener_accept_connect_retry_or_close_surface() -> None:
    value = operation()
    assert repr(value) == "ConnectedManifestHandoffSupervisorEngineApiExchange()"
    for name in ("listen", "bind", "accept", "connect", "retry", "close"):
        assert not hasattr(value, name)
