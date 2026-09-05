"""Bounded sequential serve loop for Engine API health."""

from __future__ import annotations

from dataclasses import dataclass

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_accept import (
    ControlledManifestHandoffSupervisorEngineApiHealthAccept,
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiHealthServeResult:
    exchanges: int
    reason: str

    def __post_init__(self) -> None:
        if type(self.exchanges) is not int or self.exchanges < 0 or self.reason not in (
            "stopped", "exchange_limit",
        ):
            raise ManifestHandoffRegistryUnavailable


class BoundedManifestHandoffSupervisorEngineApiHealthServeLoop:
    """Run sequential health accepts until stopped or the hard bound is reached."""

    __slots__ = ("_accept", "_maximum")

    def __init__(self, operation: ControlledManifestHandoffSupervisorEngineApiHealthAccept,
                 *, maximum_exchanges: int) -> None:
        if (type(operation) is not ControlledManifestHandoffSupervisorEngineApiHealthAccept
                or type(maximum_exchanges) is not int or maximum_exchanges < 1):
            raise ManifestHandoffRegistryUnavailable
        self._accept = operation
        self._maximum = maximum_exchanges

    def __repr__(self) -> str:
        return "BoundedManifestHandoffSupervisorEngineApiHealthServeLoop()"

    def run(self, listener, should_stop) -> ManifestHandoffSupervisorEngineApiHealthServeResult:
        exchanges = 0
        try:
            if not callable(should_stop):
                raise ManifestHandoffRegistryUnavailable
            while exchanges < self._maximum:
                stop = should_stop()
                if type(stop) is not bool:
                    raise ManifestHandoffRegistryUnavailable
                if stop:
                    return ManifestHandoffSupervisorEngineApiHealthServeResult(
                        exchanges, "stopped"
                    )
                self._accept.serve_one(listener)
                exchanges += 1
            return ManifestHandoffSupervisorEngineApiHealthServeResult(
                exchanges, "exchange_limit"
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
