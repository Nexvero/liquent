"""Listener-owned process run for the private Engine API health server."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_listener import ControlledManifestHandoffSupervisorEngineApiHealthListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_process_status import ManifestHandoffSupervisorEngineApiHealthPhase, ManifestHandoffSupervisorEngineApiHealthStatus
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_serve_loop import BoundedManifestHandoffSupervisorEngineApiHealthServeLoop


class OwnedManifestHandoffSupervisorEngineApiHealthProcessRun:
    __slots__ = ("_listener", "_loop", "_status")

    def __init__(self, listener: ControlledManifestHandoffSupervisorEngineApiHealthListener,
                 serve_loop: BoundedManifestHandoffSupervisorEngineApiHealthServeLoop,
                 status: ManifestHandoffSupervisorEngineApiHealthStatus) -> None:
        if (type(listener) is not ControlledManifestHandoffSupervisorEngineApiHealthListener
                or type(serve_loop) is not BoundedManifestHandoffSupervisorEngineApiHealthServeLoop
                or type(status) is not ManifestHandoffSupervisorEngineApiHealthStatus):
            raise ManifestHandoffRegistryUnavailable
        self._listener, self._loop, self._status = listener, serve_loop, status

    def __repr__(self) -> str:
        return "OwnedManifestHandoffSupervisorEngineApiHealthProcessRun()"

    def run(self, should_stop):
        active = None
        failed = False
        result = None
        try:
            self._status.move(ManifestHandoffSupervisorEngineApiHealthPhase.INITIAL,
                              ManifestHandoffSupervisorEngineApiHealthPhase.STARTING)
            active = self._listener.open()
            self._status.move(ManifestHandoffSupervisorEngineApiHealthPhase.STARTING,
                              ManifestHandoffSupervisorEngineApiHealthPhase.SERVING)
            result = self._loop.run(active, should_stop)
            self._status.move(ManifestHandoffSupervisorEngineApiHealthPhase.SERVING,
                              ManifestHandoffSupervisorEngineApiHealthPhase.STOPPING)
        except Exception:
            failed = True
        close_failed = False
        if active is not None:
            try:
                self._listener.close(active)
            except Exception:
                close_failed = True
        if failed or close_failed:
            try:
                self._status.fail()
            except Exception:
                pass
            raise ManifestHandoffRegistryUnavailable from None
        try:
            self._status.move(ManifestHandoffSupervisorEngineApiHealthPhase.STOPPING,
                              ManifestHandoffSupervisorEngineApiHealthPhase.STOPPED)
            return result
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
