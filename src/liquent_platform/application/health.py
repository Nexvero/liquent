"""Framework-independent process health and readiness state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Readiness:
    ready: bool
    reason: str


class ReadinessProbe(Protocol):
    def check(self) -> Readiness: ...


class ProcessHealth:
    """In-memory lifecycle state; dependency checks are added behind this port."""

    def __init__(self, probes: tuple[ReadinessProbe, ...] = ()) -> None:
        self._started = False
        self._probes = probes

    def mark_started(self) -> None:
        self._started = True

    def mark_stopping(self) -> None:
        self._started = False

    def readiness(self) -> Readiness:
        if not self._started:
            return Readiness(ready=False, reason="startup_incomplete")
        for probe in self._probes:
            result = probe.check()
            if not result.ready:
                return result
        return Readiness(ready=True, reason="ready")
