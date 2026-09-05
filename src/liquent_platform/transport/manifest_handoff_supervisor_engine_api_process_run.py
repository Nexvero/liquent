"""Fully owned bounded process run for the private Engine API proxy."""

from __future__ import annotations

from collections.abc import Callable

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_host_preflight import (
    ManifestHandoffSupervisorEngineApiHostPreflight,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener import (
    ControlledManifestHandoffSupervisorEngineApiListener,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import (
    ManifestHandoffSupervisorEngineApiProcessStatus,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import (
    BoundedManifestHandoffSupervisorEngineApiServeLoop,
    ManifestHandoffSupervisorEngineApiServeResult,
)


class OwnedManifestHandoffSupervisorEngineApiProcessRun:
    """Preflight, publish, verify, serve and retire one private listener."""

    __slots__ = (
        "_defer_terminal", "_listener", "_loop", "_preflight", "_status",
    )

    def __init__(
        self,
        preflight: ManifestHandoffSupervisorEngineApiHostPreflight,
        listener: ControlledManifestHandoffSupervisorEngineApiListener,
        serve_loop: BoundedManifestHandoffSupervisorEngineApiServeLoop,
        *,
        status: ManifestHandoffSupervisorEngineApiProcessStatus | None = None,
        defer_terminal_status: bool = False,
    ) -> None:
        status = status or ManifestHandoffSupervisorEngineApiProcessStatus()
        if (
            type(preflight) is not ManifestHandoffSupervisorEngineApiHostPreflight
            or type(listener) is not ControlledManifestHandoffSupervisorEngineApiListener
            or type(serve_loop) is not BoundedManifestHandoffSupervisorEngineApiServeLoop
            or type(status) is not ManifestHandoffSupervisorEngineApiProcessStatus
            or type(defer_terminal_status) is not bool
        ):
            raise ManifestHandoffRegistryUnavailable
        self._preflight = preflight
        self._listener = listener
        self._loop = serve_loop
        self._status = status
        self._defer_terminal = defer_terminal_status

    def __repr__(self) -> str:
        return "OwnedManifestHandoffSupervisorEngineApiProcessRun()"

    def run(
        self, stop_requested: Callable[[], bool]
    ) -> ManifestHandoffSupervisorEngineApiServeResult:
        listener = None
        result = None
        failed = False
        try:
            self._status.mark_starting()
            before = self._preflight.check_before_listener()
            if (
                before.ready is not True
                or before.reason != "manifest_handoff_supervisor_host_dependencies_ready"
            ):
                raise ManifestHandoffRegistryUnavailable
            listener = self._listener.open()
            current = self._preflight.check()
            if (
                current.ready is not True
                or current.reason != "manifest_handoff_supervisor_host_ready"
            ):
                raise ManifestHandoffRegistryUnavailable
            self._status.mark_serving()
            result = self._loop.run(listener, stop_requested)
            if type(result) is not ManifestHandoffSupervisorEngineApiServeResult:
                raise ManifestHandoffRegistryUnavailable
            self._status.mark_stopping()
        except Exception:
            failed = True
        retire_failed = False
        if listener is not None:
            try:
                self._listener.close(listener)
            except Exception:
                retire_failed = True
        if failed or retire_failed or result is None:
            try:
                self._status.mark_failed()
            except Exception:
                pass
            raise ManifestHandoffRegistryUnavailable from None
        if not self._defer_terminal:
            try:
                self._status.mark_stopped()
            except Exception:
                raise ManifestHandoffRegistryUnavailable from None
        return result

    def finalize_outer_run(self, success: bool) -> None:
        """Finalize a deliberately deferred terminal state after outer cleanup."""
        try:
            if not self._defer_terminal or type(success) is not bool:
                raise ManifestHandoffRegistryUnavailable
            current = self._status.snapshot()
            if success:
                self._status.mark_stopped()
            elif current.phase.value == "failed":
                return
            else:
                self._status.mark_failed()
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
