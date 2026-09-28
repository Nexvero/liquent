"""Detail-limited process status and readiness for the private Engine API proxy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import threading

from liquent_platform.application.health import Readiness
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ManifestHandoffSupervisorEngineApiProcessPhase(str, Enum):
    INITIAL = "initial"
    STARTING = "starting"
    SERVING = "serving"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


_REASONS = {
    ManifestHandoffSupervisorEngineApiProcessPhase.INITIAL:
        "manifest_handoff_supervisor_engine_api_initial",
    ManifestHandoffSupervisorEngineApiProcessPhase.STARTING:
        "manifest_handoff_supervisor_engine_api_starting",
    ManifestHandoffSupervisorEngineApiProcessPhase.SERVING:
        "manifest_handoff_supervisor_engine_api_ready",
    ManifestHandoffSupervisorEngineApiProcessPhase.STOPPING:
        "manifest_handoff_supervisor_engine_api_stopping",
    ManifestHandoffSupervisorEngineApiProcessPhase.STOPPED:
        "manifest_handoff_supervisor_engine_api_stopped",
    ManifestHandoffSupervisorEngineApiProcessPhase.FAILED:
        "manifest_handoff_supervisor_engine_api_unavailable",
}


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiProcessSnapshot:
    phase: ManifestHandoffSupervisorEngineApiProcessPhase
    live: bool
    ready: bool
    terminal: bool
    reason: str


class ManifestHandoffSupervisorEngineApiProcessStatus:
    """Own one monotonic, thread-safe, detail-free process lifecycle."""

    __slots__ = ("_lock", "_phase")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._phase = ManifestHandoffSupervisorEngineApiProcessPhase.INITIAL

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiProcessStatus()"

    def mark_starting(self) -> None:
        self._move(
            ManifestHandoffSupervisorEngineApiProcessPhase.INITIAL,
            ManifestHandoffSupervisorEngineApiProcessPhase.STARTING,
        )

    def mark_serving(self) -> None:
        self._move(
            ManifestHandoffSupervisorEngineApiProcessPhase.STARTING,
            ManifestHandoffSupervisorEngineApiProcessPhase.SERVING,
        )

    def mark_stopping(self) -> None:
        with self._lock:
            if self._phase not in {
                ManifestHandoffSupervisorEngineApiProcessPhase.STARTING,
                ManifestHandoffSupervisorEngineApiProcessPhase.SERVING,
            }:
                raise ManifestHandoffRegistryUnavailable
            self._phase = ManifestHandoffSupervisorEngineApiProcessPhase.STOPPING

    def mark_stopped(self) -> None:
        self._move(
            ManifestHandoffSupervisorEngineApiProcessPhase.STOPPING,
            ManifestHandoffSupervisorEngineApiProcessPhase.STOPPED,
        )

    def mark_failed(self) -> None:
        with self._lock:
            if self._phase in {
                ManifestHandoffSupervisorEngineApiProcessPhase.STOPPED,
                ManifestHandoffSupervisorEngineApiProcessPhase.FAILED,
            }:
                raise ManifestHandoffRegistryUnavailable
            self._phase = ManifestHandoffSupervisorEngineApiProcessPhase.FAILED

    def snapshot(self) -> ManifestHandoffSupervisorEngineApiProcessSnapshot:
        with self._lock:
            phase = self._phase
        terminal = phase in {
            ManifestHandoffSupervisorEngineApiProcessPhase.STOPPED,
            ManifestHandoffSupervisorEngineApiProcessPhase.FAILED,
        }
        return ManifestHandoffSupervisorEngineApiProcessSnapshot(
            phase=phase,
            live=not terminal,
            ready=phase is ManifestHandoffSupervisorEngineApiProcessPhase.SERVING,
            terminal=terminal,
            reason=_REASONS[phase],
        )

    def _move(self, expected, target) -> None:
        with self._lock:
            if self._phase is not expected:
                raise ManifestHandoffRegistryUnavailable
            self._phase = target


class ManifestHandoffSupervisorEngineApiReadinessProbe:
    """Project only current readiness and its fixed public reason."""

    __slots__ = ("_status",)

    def __init__(self, status: ManifestHandoffSupervisorEngineApiProcessStatus) -> None:
        if type(status) is not ManifestHandoffSupervisorEngineApiProcessStatus:
            raise ManifestHandoffRegistryUnavailable
        self._status = status

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiReadinessProbe()"

    def check(self) -> Readiness:
        try:
            current = self._status.snapshot()
            if type(current) is not ManifestHandoffSupervisorEngineApiProcessSnapshot:
                raise ManifestHandoffRegistryUnavailable
            return Readiness(current.ready, current.reason)
        except Exception:
            return Readiness(
                False, "manifest_handoff_supervisor_engine_api_unavailable"
            )
