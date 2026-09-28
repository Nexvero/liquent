"""Inert opt-in polling runtime for the private Engine API proxy."""

from __future__ import annotations

from dataclasses import dataclass

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import ManifestHandoffSupervisorEngineApiProcessBundle, compose_manifest_handoff_supervisor_engine_api_proxy_bundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_listener import BoundedManifestHandoffSupervisorEngineApiPollListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_loop import StopAwareManifestHandoffSupervisorEngineApiPollLoop
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_process_run import OwnedManifestHandoffSupervisorEngineApiPollProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings import ManifestHandoffSupervisorEngineApiProxySettings


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiPollRuntimeBundle:
    observed_bundle: ManifestHandoffSupervisorEngineApiProcessBundle
    listener: BoundedManifestHandoffSupervisorEngineApiPollListener
    serve_loop: StopAwareManifestHandoffSupervisorEngineApiPollLoop
    process_run: OwnedManifestHandoffSupervisorEngineApiPollProcessRun


def compose_manifest_handoff_supervisor_engine_api_poll_runtime(
    settings: ManifestHandoffSupervisorEngineApiProxySettings, *, poll_timeout_seconds: float,
) -> ManifestHandoffSupervisorEngineApiPollRuntimeBundle:
    try:
        if type(settings) is not ManifestHandoffSupervisorEngineApiProxySettings:
            raise ManifestHandoffRegistryUnavailable
        observed = compose_manifest_handoff_supervisor_engine_api_proxy_bundle(settings)
        original = observed.process_run._process
        listener = BoundedManifestHandoffSupervisorEngineApiPollListener(
            original._listener, poll_timeout_seconds=poll_timeout_seconds
        )
        serve_loop = StopAwareManifestHandoffSupervisorEngineApiPollLoop(
            original._loop._accept, maximum_exchanges=settings.maximum_exchanges
        )
        process_run = OwnedManifestHandoffSupervisorEngineApiPollProcessRun(
            original._preflight, listener, serve_loop, observed.status
        )
        return ManifestHandoffSupervisorEngineApiPollRuntimeBundle(
            observed, listener, serve_loop, process_run
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
