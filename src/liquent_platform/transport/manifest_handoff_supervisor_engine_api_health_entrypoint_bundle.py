"""Inert executable bundle for the private Engine API health process."""

from __future__ import annotations

from dataclasses import dataclass

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_signal_run import SignalOwnedManifestHandoffSupervisorEngineApiHealthRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_transport_composition import ManifestHandoffSupervisorEngineApiHealthTransportBundle
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import OwnedManifestHandoffSupervisorEngineApiSignalStopSource


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiHealthEntrypointBundle:
    transport: ManifestHandoffSupervisorEngineApiHealthTransportBundle
    signals: OwnedManifestHandoffSupervisorEngineApiSignalStopSource
    process_run: SignalOwnedManifestHandoffSupervisorEngineApiHealthRun

    def __post_init__(self) -> None:
        if (type(self.transport) is not ManifestHandoffSupervisorEngineApiHealthTransportBundle
                or type(self.signals) is not OwnedManifestHandoffSupervisorEngineApiSignalStopSource
                or type(self.process_run) is not SignalOwnedManifestHandoffSupervisorEngineApiHealthRun
                or self.process_run._signals is not self.signals
                or self.process_run._process is not self.transport.process_run):
            raise ManifestHandoffRegistryUnavailable

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiHealthEntrypointBundle()"


def compose_manifest_handoff_supervisor_engine_api_health_entrypoint(
    transport: ManifestHandoffSupervisorEngineApiHealthTransportBundle,
) -> ManifestHandoffSupervisorEngineApiHealthEntrypointBundle:
    try:
        if type(transport) is not ManifestHandoffSupervisorEngineApiHealthTransportBundle:
            raise ManifestHandoffRegistryUnavailable
        signals = OwnedManifestHandoffSupervisorEngineApiSignalStopSource()
        process_run = SignalOwnedManifestHandoffSupervisorEngineApiHealthRun(
            signals, transport.process_run
        )
        return ManifestHandoffSupervisorEngineApiHealthEntrypointBundle(
            transport, signals, process_run
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
