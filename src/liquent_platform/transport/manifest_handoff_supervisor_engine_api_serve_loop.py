"""Explicitly bounded synchronous serve loop for the private Engine API proxy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_accept import (
    ControlledManifestHandoffSupervisorEngineApiAccept,
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiServeResult:
    exchanges: int
    reason: str


class BoundedManifestHandoffSupervisorEngineApiServeLoop:
    """Serve sequential clients until explicit stop or a fixed hard limit."""

    __slots__ = ("_accept", "_maximum")

    def __init__(
        self,
        accept_operation: ControlledManifestHandoffSupervisorEngineApiAccept,
        *,
        maximum_exchanges: int,
    ) -> None:
        if (
            type(accept_operation) is not ControlledManifestHandoffSupervisorEngineApiAccept
            or type(maximum_exchanges) is not int
            or maximum_exchanges < 1
        ):
            raise ManifestHandoffRegistryUnavailable
        self._accept = accept_operation
        self._maximum = maximum_exchanges

    def __repr__(self) -> str:
        return "BoundedManifestHandoffSupervisorEngineApiServeLoop()"

    def run(
        self, listener, stop_requested: Callable[[], bool]
    ) -> ManifestHandoffSupervisorEngineApiServeResult:
        try:
            if not callable(stop_requested):
                raise ManifestHandoffRegistryUnavailable
            exchanges = 0
            while exchanges < self._maximum:
                stopped = stop_requested()
                if type(stopped) is not bool:
                    raise ManifestHandoffRegistryUnavailable
                if stopped:
                    return ManifestHandoffSupervisorEngineApiServeResult(
                        exchanges, "stopped"
                    )
                self._accept.serve_one(listener)
                exchanges += 1
            return ManifestHandoffSupervisorEngineApiServeResult(
                exchanges, "exchange_limit"
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
