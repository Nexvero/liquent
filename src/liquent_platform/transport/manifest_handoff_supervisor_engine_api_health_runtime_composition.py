"""Controlled health runtime composition bound to the observed process bundle."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import ManifestHandoffSupervisorEngineApiProcessBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority import ManifestHandoffSupervisorEngineApiHealthSocketAuthority
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_composition import compose_manifest_handoff_supervisor_engine_api_health
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_entrypoint_bundle import compose_manifest_handoff_supervisor_engine_api_health_entrypoint
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_entrypoint_owner import ManifestHandoffSupervisorEngineApiHealthEntrypointOwner
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_run_settings import ManifestHandoffSupervisorEngineApiHealthRunSettings
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_transport_composition import compose_manifest_handoff_supervisor_engine_api_health_transport


def compose_manifest_handoff_supervisor_engine_api_health_runtime(
    process_bundle: ManifestHandoffSupervisorEngineApiProcessBundle,
    authority: ManifestHandoffSupervisorEngineApiHealthSocketAuthority,
    settings: ManifestHandoffSupervisorEngineApiHealthRunSettings,
) -> ManifestHandoffSupervisorEngineApiHealthEntrypointOwner:
    try:
        if (type(process_bundle) is not ManifestHandoffSupervisorEngineApiProcessBundle
                or type(authority) is not ManifestHandoffSupervisorEngineApiHealthSocketAuthority
                or type(settings) is not ManifestHandoffSupervisorEngineApiHealthRunSettings):
            raise ManifestHandoffRegistryUnavailable
        health = compose_manifest_handoff_supervisor_engine_api_health(
            process_bundle, authority
        )
        transport = compose_manifest_handoff_supervisor_engine_api_health_transport(
            health, maximum_exchanges=settings.maximum_exchanges
        )
        entrypoint = compose_manifest_handoff_supervisor_engine_api_health_entrypoint(
            transport
        )
        return ManifestHandoffSupervisorEngineApiHealthEntrypointOwner(entrypoint)
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
