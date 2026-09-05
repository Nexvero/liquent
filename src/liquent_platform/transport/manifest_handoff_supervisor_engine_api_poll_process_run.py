"""Fully owned polling process run for the private Engine API proxy."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_host_preflight import ManifestHandoffSupervisorEngineApiHostPreflight
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_listener import BoundedManifestHandoffSupervisorEngineApiPollListener
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_loop import StopAwareManifestHandoffSupervisorEngineApiPollLoop
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_status import ManifestHandoffSupervisorEngineApiProcessStatus
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import ManifestHandoffSupervisorEngineApiServeResult


class OwnedManifestHandoffSupervisorEngineApiPollProcessRun:
    __slots__ = ("_listener", "_loop", "_preflight", "_status")

    def __init__(self, preflight: ManifestHandoffSupervisorEngineApiHostPreflight,
                 listener: BoundedManifestHandoffSupervisorEngineApiPollListener,
                 serve_loop: StopAwareManifestHandoffSupervisorEngineApiPollLoop,
                 status: ManifestHandoffSupervisorEngineApiProcessStatus) -> None:
        if (type(preflight) is not ManifestHandoffSupervisorEngineApiHostPreflight
                or type(listener) is not BoundedManifestHandoffSupervisorEngineApiPollListener
                or type(serve_loop) is not StopAwareManifestHandoffSupervisorEngineApiPollLoop
                or type(status) is not ManifestHandoffSupervisorEngineApiProcessStatus):
            raise ManifestHandoffRegistryUnavailable
        self._preflight, self._listener = preflight, listener
        self._loop, self._status = serve_loop, status

    def run(self, should_stop) -> ManifestHandoffSupervisorEngineApiServeResult:
        active = None
        result = None
        failed = False
        try:
            self._status.mark_starting()
            if self._preflight.check_before_listener().ready is not True:
                raise ManifestHandoffRegistryUnavailable
            active = self._listener.open()
            if self._preflight.check().ready is not True:
                raise ManifestHandoffRegistryUnavailable
            self._status.mark_serving()
            result = self._loop.run(active, should_stop)
            if type(result) is not ManifestHandoffSupervisorEngineApiServeResult:
                raise ManifestHandoffRegistryUnavailable
            self._status.mark_stopping()
        except Exception:
            failed = True
        close_failed = False
        if active is not None:
            try: self._listener.close(active)
            except Exception: close_failed = True
        if failed or close_failed or result is None:
            try: self._status.mark_failed()
            except Exception: pass
            raise ManifestHandoffRegistryUnavailable from None
        try:
            self._status.mark_stopped()
            return result
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def __repr__(self) -> str:
        return "OwnedManifestHandoffSupervisorEngineApiPollProcessRun()"
