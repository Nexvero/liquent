"""Stop-aware bounded polling loop for Engine API health."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_accept import BoundedManifestHandoffSupervisorEngineApiHealthPollAccept, ManifestHandoffSupervisorEngineApiHealthPollResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_serve_loop import ManifestHandoffSupervisorEngineApiHealthServeResult


class StopAwareManifestHandoffSupervisorEngineApiHealthPollLoop:
    __slots__ = ("_accept", "_maximum")

    def __init__(self, operation: BoundedManifestHandoffSupervisorEngineApiHealthPollAccept,
                 *, maximum_exchanges: int) -> None:
        if (type(operation) is not BoundedManifestHandoffSupervisorEngineApiHealthPollAccept
                or type(maximum_exchanges) is not int or maximum_exchanges < 1):
            raise ManifestHandoffRegistryUnavailable
        self._accept, self._maximum = operation, maximum_exchanges

    def run(self, listener, should_stop) -> ManifestHandoffSupervisorEngineApiHealthServeResult:
        served = 0
        try:
            if not callable(should_stop):
                raise ManifestHandoffRegistryUnavailable
            while served < self._maximum:
                stop = should_stop()
                if type(stop) is not bool:
                    raise ManifestHandoffRegistryUnavailable
                if stop:
                    return ManifestHandoffSupervisorEngineApiHealthServeResult(served, "stopped")
                result = self._accept.poll_one(listener)
                if type(result) is not ManifestHandoffSupervisorEngineApiHealthPollResult:
                    raise ManifestHandoffRegistryUnavailable
                if result.served:
                    served += 1
            return ManifestHandoffSupervisorEngineApiHealthServeResult(served, "exchange_limit")
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
