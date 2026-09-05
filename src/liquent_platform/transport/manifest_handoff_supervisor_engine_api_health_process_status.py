"""Detail-free lifecycle status for the private Engine API health server."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import threading

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ManifestHandoffSupervisorEngineApiHealthPhase(str, Enum):
    INITIAL = "initial"
    STARTING = "starting"
    SERVING = "serving"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiHealthSnapshot:
    phase: ManifestHandoffSupervisorEngineApiHealthPhase
    live: bool
    ready: bool
    terminal: bool


class ManifestHandoffSupervisorEngineApiHealthStatus:
    __slots__ = ("_lock", "_phase")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._phase = ManifestHandoffSupervisorEngineApiHealthPhase.INITIAL

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiHealthStatus()"

    def move(self, expected: ManifestHandoffSupervisorEngineApiHealthPhase,
             target: ManifestHandoffSupervisorEngineApiHealthPhase) -> None:
        if type(expected) is not ManifestHandoffSupervisorEngineApiHealthPhase or type(target) is not ManifestHandoffSupervisorEngineApiHealthPhase:
            raise ManifestHandoffRegistryUnavailable
        with self._lock:
            if self._phase is not expected:
                raise ManifestHandoffRegistryUnavailable
            self._phase = target

    def fail(self) -> None:
        with self._lock:
            if self._phase in (ManifestHandoffSupervisorEngineApiHealthPhase.STOPPED,
                                ManifestHandoffSupervisorEngineApiHealthPhase.FAILED):
                raise ManifestHandoffRegistryUnavailable
            self._phase = ManifestHandoffSupervisorEngineApiHealthPhase.FAILED

    def snapshot(self) -> ManifestHandoffSupervisorEngineApiHealthSnapshot:
        with self._lock:
            phase = self._phase
        terminal = phase in (ManifestHandoffSupervisorEngineApiHealthPhase.STOPPED,
                             ManifestHandoffSupervisorEngineApiHealthPhase.FAILED)
        return ManifestHandoffSupervisorEngineApiHealthSnapshot(
            phase, not terminal,
            phase is ManifestHandoffSupervisorEngineApiHealthPhase.SERVING,
            terminal,
        )
