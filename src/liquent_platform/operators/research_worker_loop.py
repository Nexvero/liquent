"""Bounded serial loop for the controlled single-job research processor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math

from liquent_platform.application.process_research_job import (
    ProcessOneResearchJob,
    ResearchJobProcessingUnavailable,
    ResearchWorkResultKind,
)
from liquent_platform.identity.research import ResearchWorkerId
from liquent_platform.persistence.identity_errors import ResearchJobStoreUnavailable
from liquent_platform.persistence.research_artifacts import (
    ResearchArtifactStoreUnavailable,
)


@dataclass(frozen=True, slots=True)
class ResearchWorkerLoopPolicy:
    idle_wait_seconds: float
    unavailable_initial_wait_seconds: float
    unavailable_max_wait_seconds: float
    jitter_max_seconds: float

    def __post_init__(self) -> None:
        values = (
            self.idle_wait_seconds,
            self.unavailable_initial_wait_seconds,
            self.unavailable_max_wait_seconds,
            self.jitter_max_seconds,
        )
        if any(
            type(value) not in (int, float)
            or not math.isfinite(value)
            or value < 0
            for value in values
        ):
            raise ValueError("research worker loop waits must be non-negative")
        if self.idle_wait_seconds <= 0 or self.unavailable_initial_wait_seconds <= 0:
            raise ValueError("research worker loop base waits must be positive")
        if self.unavailable_max_wait_seconds < self.unavailable_initial_wait_seconds:
            raise ValueError("research worker maximum wait must cover initial wait")


@dataclass(frozen=True, slots=True)
class ResearchWorkerLoopResult:
    succeeded: int
    failed: int
    claims_lost: int
    technical_unavailability: int


class ResearchWorkerLoop:
    """Process jobs serially until an externally owned stop event is set."""

    __slots__ = ("_processor", "_worker_id", "_policy", "_jitter")

    def __init__(
        self,
        processor: ProcessOneResearchJob,
        worker_id: ResearchWorkerId,
        policy: ResearchWorkerLoopPolicy,
        *,
        jitter: Callable[[float], float],
    ) -> None:
        if type(worker_id) is not ResearchWorkerId:
            raise ValueError("research worker id is required")
        self._processor = processor
        self._worker_id = worker_id
        self._policy = policy
        self._jitter = jitter

    def __repr__(self) -> str:
        return "ResearchWorkerLoop()"

    def run(
        self,
        *,
        stop_requested: Callable[[], bool],
        wait: Callable[[float], bool],
    ) -> ResearchWorkerLoopResult:
        succeeded = failed = claims_lost = unavailable = 0
        technical_wait = self._policy.unavailable_initial_wait_seconds

        while not stop_requested():
            try:
                result = self._processor.process(self._worker_id)
            except (
                ResearchJobStoreUnavailable,
                ResearchJobProcessingUnavailable,
                ResearchArtifactStoreUnavailable,
            ):
                unavailable += 1
                if self._wait(wait, technical_wait):
                    break
                technical_wait = min(
                    technical_wait * 2,
                    self._policy.unavailable_max_wait_seconds,
                )
                continue

            technical_wait = self._policy.unavailable_initial_wait_seconds
            if result.kind is ResearchWorkResultKind.IDLE:
                if self._wait(wait, self._policy.idle_wait_seconds):
                    break
            elif result.kind is ResearchWorkResultKind.SUCCEEDED:
                succeeded += 1
            elif result.kind is ResearchWorkResultKind.FAILED:
                failed += 1
            elif result.kind is ResearchWorkResultKind.CLAIM_LOST:
                claims_lost += 1
                if self._wait(wait, technical_wait):
                    break
            else:
                raise RuntimeError("unsupported research work result")

        return ResearchWorkerLoopResult(succeeded, failed, claims_lost, unavailable)

    def _wait(self, wait: Callable[[float], bool], base: float) -> bool:
        jitter = self._jitter(self._policy.jitter_max_seconds)
        if (
            type(jitter) not in (int, float)
            or not math.isfinite(jitter)
            or not 0 <= jitter <= self._policy.jitter_max_seconds
        ):
            raise ValueError("research worker jitter is outside policy")
        return wait(base + jitter)
