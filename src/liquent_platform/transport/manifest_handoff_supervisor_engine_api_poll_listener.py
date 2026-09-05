"""Polling-timeout wrapper for the controlled private Engine API listener."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_listener import ControlledManifestHandoffSupervisorEngineApiListener


class BoundedManifestHandoffSupervisorEngineApiPollListener:
    __slots__ = ("_listener", "_timeout")

    def __init__(self, listener: ControlledManifestHandoffSupervisorEngineApiListener,
                 *, poll_timeout_seconds: float) -> None:
        if (type(listener) is not ControlledManifestHandoffSupervisorEngineApiListener
                or type(poll_timeout_seconds) not in (int, float)
                or isinstance(poll_timeout_seconds, bool)
                or poll_timeout_seconds <= 0 or poll_timeout_seconds > 60):
            raise ManifestHandoffRegistryUnavailable
        self._listener = listener
        self._timeout = float(poll_timeout_seconds)

    def open(self):
        active = None
        try:
            active = self._listener.open()
            active.settimeout(self._timeout)
            if active.gettimeout() != self._timeout:
                raise ManifestHandoffRegistryUnavailable
            return active
        except Exception:
            if active is not None:
                try:
                    self._listener.close(active)
                except Exception:
                    pass
            raise ManifestHandoffRegistryUnavailable from None

    def close(self, active) -> None:
        try:
            self._listener.close(active)
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def __repr__(self) -> str:
        return "BoundedManifestHandoffSupervisorEngineApiPollListener()"
