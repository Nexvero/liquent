"""Complete inert dependency composition for the private Engine API proxy."""

from __future__ import annotations

from dataclasses import dataclass

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_accept import (
    ControlledManifestHandoffSupervisorEngineApiAccept,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import (
    LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_connected_exchange import (
    ConnectedManifestHandoffSupervisorEngineApiExchange,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_connector import (
    ControlledManifestHandoffSupervisorEngineApiDaemonConnector,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_peer import (
    LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_exchange import (
    ClosedManifestHandoffSupervisorEngineApiExchange,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_gate import (
    ClosedManifestHandoffSupervisorEngineApiGate,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_host_preflight import (
    ManifestHandoffSupervisorEngineApiHostPreflight,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener import (
    ControlledManifestHandoffSupervisorEngineApiListener,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_run import (
    OwnedManifestHandoffSupervisorEngineApiProcessRun,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import (
    ManifestHandoffSupervisorEngineApiReadinessProbe,
    ManifestHandoffSupervisorEngineApiProcessStatus,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import (
    ClosedManifestHandoffSupervisorCreateRequestPolicy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import (
    BoundedManifestHandoffSupervisorEngineApiServeLoop,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import (
    ManifestHandoffSupervisorEngineApiProxySettings,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_signal_run import (
    SignalOwnedManifestHandoffSupervisorEngineApiRun,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import (
    OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_verified_exchange import (
    VerifiedManifestHandoffSupervisorEngineApiExchange,
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiProcessBundle:
    process_run: SignalOwnedManifestHandoffSupervisorEngineApiRun
    status: ManifestHandoffSupervisorEngineApiProcessStatus
    readiness: ManifestHandoffSupervisorEngineApiReadinessProbe

    def __post_init__(self) -> None:
        if (
            type(self.process_run) is not SignalOwnedManifestHandoffSupervisorEngineApiRun
            or type(self.status) is not ManifestHandoffSupervisorEngineApiProcessStatus
            or type(self.readiness) is not ManifestHandoffSupervisorEngineApiReadinessProbe
            or self.process_run._process._status is not self.status
            or self.readiness._status is not self.status
        ):
            raise ManifestHandoffRegistryUnavailable

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiProcessBundle()"


def compose_manifest_handoff_supervisor_engine_api_proxy_bundle(
    settings: ManifestHandoffSupervisorEngineApiProxySettings,
) -> ManifestHandoffSupervisorEngineApiProcessBundle:
    """Build one complete graph without reading host state or opening sockets."""
    if type(settings) is not ManifestHandoffSupervisorEngineApiProxySettings:
        raise ManifestHandoffRegistryUnavailable
    try:
        create = ClosedManifestHandoffSupervisorCreateRequestPolicy(
            control_root=settings.control_root,
            source_root=settings.source_root,
            target_root=settings.target_root,
            writer_command=settings.writer_command,
            recovery_command=settings.recovery_command,
            wrapper_uid=settings.wrapper_uid,
            wrapper_gid=settings.wrapper_gid,
        )
        gate = ClosedManifestHandoffSupervisorEngineApiGate(create)
        exchange = ClosedManifestHandoffSupervisorEngineApiExchange(gate)
        client = LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy(
            local_socket=settings.proxy_socket,
            client_uid=settings.host_owner_uid,
            client_gid=settings.client_gid,
            timeout_seconds=settings.client_timeout_seconds,
        )
        daemon = LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy(
            daemon_socket=settings.daemon_socket,
            daemon_uid=settings.daemon_uid,
            daemon_gid=settings.daemon_gid,
            timeout_seconds=settings.daemon_timeout_seconds,
        )
        verified = VerifiedManifestHandoffSupervisorEngineApiExchange(
            client, daemon, exchange
        )
        connector = ControlledManifestHandoffSupervisorEngineApiDaemonConnector(
            daemon_socket=settings.daemon_socket,
            timeout_seconds=settings.daemon_timeout_seconds,
        )
        connected = ConnectedManifestHandoffSupervisorEngineApiExchange(
            connector, verified
        )
        accept = ControlledManifestHandoffSupervisorEngineApiAccept(
            socket_path=settings.proxy_socket,
            client_timeout_seconds=settings.client_timeout_seconds,
            exchange=connected,
        )
        serve_loop = BoundedManifestHandoffSupervisorEngineApiServeLoop(
            accept, maximum_exchanges=settings.maximum_exchanges
        )
        preflight = ManifestHandoffSupervisorEngineApiHostPreflight(
            proxy_socket=settings.proxy_socket,
            daemon_socket=settings.daemon_socket,
            control_root=settings.control_root,
            source_root=settings.source_root,
            target_root=settings.target_root,
            proxy_uid=settings.proxy_uid,
            client_gid=settings.client_gid,
            daemon_uid=settings.daemon_uid,
            daemon_gid=settings.daemon_gid,
            host_owner_uid=settings.host_owner_uid,
            host_owner_gid=settings.host_owner_gid,
            data_owner_uid=settings.data_owner_uid,
            data_gid=settings.data_gid,
        )
        listener = ControlledManifestHandoffSupervisorEngineApiListener(
            socket_path=settings.proxy_socket,
            proxy_uid=settings.proxy_uid,
            client_gid=settings.client_gid,
            parent_uid=settings.host_owner_uid,
            parent_gid=settings.host_owner_gid,
            backlog=settings.listener_backlog,
        )
        status = ManifestHandoffSupervisorEngineApiProcessStatus()
        process = OwnedManifestHandoffSupervisorEngineApiProcessRun(
            preflight, listener, serve_loop, status=status,
            defer_terminal_status=True,
        )
        signals = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
        process_run = SignalOwnedManifestHandoffSupervisorEngineApiRun(
            signals, process
        )
        readiness = ManifestHandoffSupervisorEngineApiReadinessProbe(status)
        return ManifestHandoffSupervisorEngineApiProcessBundle(
            process_run, status, readiness
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None


def compose_manifest_handoff_supervisor_engine_api_proxy(
    settings: ManifestHandoffSupervisorEngineApiProxySettings,
) -> SignalOwnedManifestHandoffSupervisorEngineApiRun:
    """Compatibility projection of the complete inert process bundle."""
    return compose_manifest_handoff_supervisor_engine_api_proxy_bundle(
        settings
    ).process_run
