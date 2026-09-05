"""Inert polling health runtime bound to one observed process bundle."""

from __future__ import annotations

from dataclasses import dataclass

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import ManifestHandoffSupervisorEngineApiProcessBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority import ManifestHandoffSupervisorEngineApiHealthSocketAuthority
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_composition import ManifestHandoffSupervisorEngineApiHealthBundle, compose_manifest_handoff_supervisor_engine_api_health
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_exchange import VerifiedManifestHandoffSupervisorEngineApiHealthExchange
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_listener import ControlledManifestHandoffSupervisorEngineApiHealthListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_accept import BoundedManifestHandoffSupervisorEngineApiHealthPollAccept
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_listener import BoundedManifestHandoffSupervisorEngineApiHealthPollListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_loop import StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_process_run import OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_process_status import ManifestHandoffSupervisorEngineApiHealthStatus
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_run_settings import ManifestHandoffSupervisorEngineApiHealthRunSettings


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiHealthPollRuntimeBundle:
    health: ManifestHandoffSupervisorEngineApiHealthBundle
    listener: BoundedManifestHandoffSupervisorEngineApiHealthPollListener
    serve_loop: StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop
    status: ManifestHandoffSupervisorEngineApiHealthStatus
    process_run: OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun


def compose_manifest_handoff_supervisor_engine_api_health_poll_runtime(
    process: ManifestHandoffSupervisorEngineApiProcessBundle,
    authority: ManifestHandoffSupervisorEngineApiHealthSocketAuthority,
    settings: ManifestHandoffSupervisorEngineApiHealthRunSettings,
    *, poll_timeout_seconds: float,
) -> ManifestHandoffSupervisorEngineApiHealthPollRuntimeBundle:
    try:
        if (type(process) is not ManifestHandoffSupervisorEngineApiProcessBundle
                or type(authority) is not ManifestHandoffSupervisorEngineApiHealthSocketAuthority
                or type(settings) is not ManifestHandoffSupervisorEngineApiHealthRunSettings):
            raise ManifestHandoffRegistryUnavailable
        health = compose_manifest_handoff_supervisor_engine_api_health(process, authority)
        exchange = VerifiedManifestHandoffSupervisorEngineApiHealthExchange(
            health.peer_policy, health.protocol
        )
        poll_accept = BoundedManifestHandoffSupervisorEngineApiHealthPollAccept(
            socket_path=authority.socket_path, poll_timeout_seconds=poll_timeout_seconds,
            client_timeout_seconds=authority.timeout_seconds, exchange=exchange,
        )
        base_listener = ControlledManifestHandoffSupervisorEngineApiHealthListener(
            socket_path=authority.socket_path, socket_uid=authority.socket_uid,
            client_gid=authority.socket_gid, parent_uid=authority.parent_uid,
            parent_gid=authority.parent_gid, backlog=authority.backlog,
        )
        listener = BoundedManifestHandoffSupervisorEngineApiHealthPollListener(
            base_listener, poll_timeout_seconds=poll_timeout_seconds
        )
        serve_loop = StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop(
            poll_accept, maximum_exchanges=settings.maximum_exchanges
        )
        status = ManifestHandoffSupervisorEngineApiHealthStatus()
        process_run = OwnedManifestHandoffSupervisorEngineApiHealthPollProcessRun(
            listener, serve_loop, status
        )
        return ManifestHandoffSupervisorEngineApiHealthPollRuntimeBundle(
            health, listener, serve_loop, status, process_run
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
