"""Signal-owned finite run for the private Engine API health process."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_process_run import OwnedManifestHandoffSupervisorEngineApiHealthProcessRun
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_serve_loop import ManifestHandoffSupervisorEngineApiHealthServeResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import OwnedManifestHandoffSupervisorEngineApiSignalStopSource


class SignalOwnedManifestHandoffSupervisorEngineApiHealthRun:
    __slots__ = ("_process", "_signals")

    def __init__(self, signals: OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
                 process: OwnedManifestHandoffSupervisorEngineApiHealthProcessRun) -> None:
        if (type(signals) is not OwnedManifestHandoffSupervisorEngineApiSignalStopSource
                or type(process) is not OwnedManifestHandoffSupervisorEngineApiHealthProcessRun):
            raise ManifestHandoffRegistryUnavailable
        self._signals, self._process = signals, process

    def __repr__(self) -> str:
        return "SignalOwnedManifestHandoffSupervisorEngineApiHealthRun()"

    def run(self) -> ManifestHandoffSupervisorEngineApiHealthServeResult:
        installed = False
        failed = False
        result = None
        try:
            self._signals.install()
            installed = True
            result = self._process.run(self._signals.requested)
            if type(result) is not ManifestHandoffSupervisorEngineApiHealthServeResult:
                raise ManifestHandoffRegistryUnavailable
        except Exception:
            failed = True
        restore_failed = False
        if installed:
            try:
                self._signals.restore()
            except Exception:
                restore_failed = True
        if failed or restore_failed or result is None:
            raise ManifestHandoffRegistryUnavailable from None
        return result
