"""Stop-aware bounded polling loop for the private Engine API proxy."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_accept import ControlledManifestHandoffSupervisorEngineApiAccept, ManifestHandoffSupervisorEngineApiAcceptPollResult
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_serve_loop import ManifestHandoffSupervisorEngineApiServeResult


class StopAwareManifestHandoffSupervisorEngineApiPollLoop:
    __slots__ = ("_accept", "_maximum")

    def __init__(self, operation: ControlledManifestHandoffSupervisorEngineApiAccept,
                 *, maximum_exchanges: int) -> None:
        if (type(operation) is not ControlledManifestHandoffSupervisorEngineApiAccept
                or type(maximum_exchanges) is not int or maximum_exchanges < 1):
            raise ManifestHandoffRegistryUnavailable
        self._accept, self._maximum = operation, maximum_exchanges

    def run(self, listener, should_stop) -> ManifestHandoffSupervisorEngineApiServeResult:
        served = 0
        try:
            if not callable(should_stop):
                raise ManifestHandoffRegistryUnavailable
            while served < self._maximum:
                stop = should_stop()
                if type(stop) is not bool:
                    raise ManifestHandoffRegistryUnavailable
                if stop:
                    return ManifestHandoffSupervisorEngineApiServeResult(served, "stopped")
                result = self._accept.poll_one(listener)
                if type(result) is not ManifestHandoffSupervisorEngineApiAcceptPollResult:
                    raise ManifestHandoffRegistryUnavailable
                if result.served:
                    served += 1
            return ManifestHandoffSupervisorEngineApiServeResult(served, "exchange_limit")
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
