"""Signal-owned finite run for the private Engine API proxy process."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_run import (
    OwnedManifestHandoffSupervisorEngineApiProcessRun,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import (
    ManifestHandoffSupervisorEngineApiServeResult,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stop_source import (
    OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
)


class SignalOwnedManifestHandoffSupervisorEngineApiRun:
    """Install signals, run once and restore signals on every installed path."""

    __slots__ = ("_process", "_signals")

    def __init__(
        self,
        signals: OwnedManifestHandoffSupervisorEngineApiSignalStopSource,
        process_run: OwnedManifestHandoffSupervisorEngineApiProcessRun,
    ) -> None:
        if (
            type(signals) is not OwnedManifestHandoffSupervisorEngineApiSignalStopSource
            or type(process_run) is not OwnedManifestHandoffSupervisorEngineApiProcessRun
        ):
            raise ManifestHandoffRegistryUnavailable
        self._signals = signals
        self._process = process_run

    def __repr__(self) -> str:
        return "SignalOwnedManifestHandoffSupervisorEngineApiRun()"

    def run(self) -> ManifestHandoffSupervisorEngineApiServeResult:
        installed = False
        result = None
        failed = False
        try:
            self._signals.install()
            installed = True
            stop_requested = self._signals.requested
            result = self._process.run(stop_requested)
            if type(result) is not ManifestHandoffSupervisorEngineApiServeResult:
                raise ManifestHandoffRegistryUnavailable
        except Exception:
            failed = True
        restore_failed = False
        if installed:
            try:
                self._signals.restore()
            except Exception:
                restore_failed = True
        deferred = getattr(self._process, "_defer_terminal", False) is True
        if deferred:
            try:
                self._process.finalize_outer_run(
                    not failed and not restore_failed and result is not None
                )
            except Exception:
                failed = True
        if failed or restore_failed or result is None:
            raise ManifestHandoffRegistryUnavailable from None
        return result
