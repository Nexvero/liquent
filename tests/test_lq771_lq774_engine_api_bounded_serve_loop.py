from pathlib import Path

import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_accept import ControlledManifestHandoffSupervisorEngineApiAccept
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_connected_exchange import ConnectedManifestHandoffSupervisorEngineApiExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_connector import ControlledManifestHandoffSupervisorEngineApiDaemonConnector
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_peer import LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_exchange import ClosedManifestHandoffSupervisorEngineApiExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_gate import ClosedManifestHandoffSupervisorEngineApiGate
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import ClosedManifestHandoffSupervisorCreateRequestPolicy
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import BoundedManifestHandoffSupervisorEngineApiServeLoop, ManifestHandoffSupervisorEngineApiServeResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_verified_exchange import VerifiedManifestHandoffSupervisorEngineApiExchange


CLIENT = Path("/run/liquent/engine.sock")
DAEMON = Path("/var/run/docker.sock")


def accept_operation():
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
    connected = ConnectedManifestHandoffSupervisorEngineApiExchange(
        ControlledManifestHandoffSupervisorEngineApiDaemonConnector(
            daemon_socket=DAEMON, timeout_seconds=5.0,
            socket_factory=lambda family, kind: None,
        ),
        verified,
    )
    return ControlledManifestHandoffSupervisorEngineApiAccept(
        socket_path=CLIENT, client_timeout_seconds=5.0, exchange=connected,
    )


def loop(maximum=3):
    return BoundedManifestHandoffSupervisorEngineApiServeLoop(
        accept_operation(), maximum_exchanges=maximum,
    )


def test_stop_before_first_exchange_has_no_accept_effect(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiAccept,
        "serve_one", lambda self, listener: calls.append(listener),
    )
    listener = object()
    assert loop().run(listener, lambda: True) == (
        ManifestHandoffSupervisorEngineApiServeResult(0, "stopped")
    )
    assert calls == []


def test_stop_is_checked_once_between_sequential_exchanges(monkeypatch) -> None:
    events = []
    decisions = iter((False, False, True))

    def stop():
        events.append("stop")
        return next(decisions)

    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiAccept,
        "serve_one", lambda self, listener: events.append("exchange"),
    )
    assert loop(maximum=5).run(object(), stop) == (
        ManifestHandoffSupervisorEngineApiServeResult(2, "stopped")
    )
    assert events == ["stop", "exchange", "stop", "exchange", "stop"]


def test_hard_exchange_limit_terminates_without_extra_stop_or_accept(monkeypatch) -> None:
    stops, accepts = [], []
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiAccept,
        "serve_one", lambda self, listener: accepts.append(listener),
    )
    result = loop(maximum=3).run(object(), lambda: stops.append(True) or False)
    assert result == ManifestHandoffSupervisorEngineApiServeResult(3, "exchange_limit")
    assert len(stops) == len(accepts) == 3


def test_accept_failure_stops_immediately_without_retry(monkeypatch) -> None:
    calls = []

    def fail(self, listener):
        calls.append(listener)
        raise RuntimeError("secret")

    monkeypatch.setattr(ControlledManifestHandoffSupervisorEngineApiAccept, "serve_one", fail)
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        loop(maximum=5).run(object(), lambda: False)
    assert len(calls) == 1
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("stop", (
    None,
    lambda: None,
    lambda: 1,
    lambda: (_ for _ in ()).throw(RuntimeError("secret")),
))
def test_invalid_or_failed_stop_source_is_detail_free_before_accept(monkeypatch, stop) -> None:
    calls = []
    monkeypatch.setattr(
        ControlledManifestHandoffSupervisorEngineApiAccept,
        "serve_one", lambda *args: calls.append("accept"),
    )
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        loop().run(object(), stop)
    assert calls == []
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("operation,maximum", (
    (object(), 1),
    (accept_operation(), 0),
    (accept_operation(), True),
))
def test_invalid_composition_or_limit_fails_at_construction(operation, maximum) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        BoundedManifestHandoffSupervisorEngineApiServeLoop(
            operation, maximum_exchanges=maximum,
        )


def test_loop_has_no_listener_lifecycle_signal_thread_or_close_surface() -> None:
    value = loop()
    assert repr(value) == "BoundedManifestHandoffSupervisorEngineApiServeLoop()"
    for name in ("open", "listen", "bind", "signal", "thread", "close"):
        assert not hasattr(value, name)
