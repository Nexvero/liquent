"""Inert composition for the complete private Engine API health transport."""

from __future__ import annotations

from dataclasses import dataclass

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_accept import ControlledManifestHandoffSupervisorEngineApiHealthAccept
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_composition import ManifestHandoffSupervisorEngineApiHealthBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_exchange import VerifiedManifestHandoffSupervisorEngineApiHealthExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_listener import ControlledManifestHandoffSupervisorEngineApiHealthListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_process_run import OwnedManifestHandoffSupervisorEngineApiHealthProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_process_status import ManifestHandoffSupervisorEngineApiHealthStatus
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_serve_loop import BoundedManifestHandoffSupervisorEngineApiHealthServeLoop


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiHealthTransportBundle:
    health: ManifestHandoffSupervisorEngineApiHealthBundle
    exchange: VerifiedManifestHandoffSupervisorEngineApiHealthExchange
    accept: ControlledManifestHandoffSupervisorEngineApiHealthAccept
    listener: ControlledManifestHandoffSupervisorEngineApiHealthListener
    serve_loop: BoundedManifestHandoffSupervisorEngineApiHealthServeLoop
    status: ManifestHandoffSupervisorEngineApiHealthStatus
    process_run: OwnedManifestHandoffSupervisorEngineApiHealthProcessRun

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiHealthTransportBundle()"


def compose_manifest_handoff_supervisor_engine_api_health_transport(
    health: ManifestHandoffSupervisorEngineApiHealthBundle, *, maximum_exchanges: int,
) -> ManifestHandoffSupervisorEngineApiHealthTransportBundle:
    try:
        if type(health) is not ManifestHandoffSupervisorEngineApiHealthBundle:
            raise ManifestHandoffRegistryUnavailable
        authority = health.authority
        exchange = VerifiedManifestHandoffSupervisorEngineApiHealthExchange(
            health.peer_policy, health.protocol
        )
        accept = ControlledManifestHandoffSupervisorEngineApiHealthAccept(
            socket_path=authority.socket_path,
            client_timeout_seconds=authority.timeout_seconds, exchange=exchange,
        )
        listener = ControlledManifestHandoffSupervisorEngineApiHealthListener(
            socket_path=authority.socket_path, socket_uid=authority.socket_uid,
            client_gid=authority.socket_gid, parent_uid=authority.parent_uid,
            parent_gid=authority.parent_gid, backlog=authority.backlog,
        )
        serve_loop = BoundedManifestHandoffSupervisorEngineApiHealthServeLoop(
            accept, maximum_exchanges=maximum_exchanges,
        )
        status = ManifestHandoffSupervisorEngineApiHealthStatus()
        process_run = OwnedManifestHandoffSupervisorEngineApiHealthProcessRun(
            listener, serve_loop, status
        )
        return ManifestHandoffSupervisorEngineApiHealthTransportBundle(
            health, exchange, accept, listener, serve_loop, status, process_run
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
