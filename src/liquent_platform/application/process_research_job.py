"""Execute at most one persistently claimed research job."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from enum import Enum

from liquent_platform.application.evidence import evidence_document
from liquent_platform.application.ports import ArtifactStore
from liquent_platform.application.research import BacktestExecution, execute_local_research
from liquent_platform.application.start_research import ResearchRunnerResolver
from liquent_platform.application.persistent_research_jobs import (
    PersistentResearchWorkerControl,
)
from liquent_platform.identity.research import ResearchWorkerId
from liquent_platform.identity.research_job import (
    CompletedResearchJob,
    ResearchJobFailureCode,
)


class ResearchWorkResultKind(str, Enum):
    IDLE = "idle"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CLAIM_LOST = "claim_lost"


class ResearchJobProcessingUnavailable(Exception):
    code = "research_job_processing_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ResearchWorkResult:
    kind: ResearchWorkResultKind
    completed: CompletedResearchJob | None = None

    def __post_init__(self) -> None:
        terminal = self.kind in {
            ResearchWorkResultKind.SUCCEEDED,
            ResearchWorkResultKind.FAILED,
        }
        if terminal != (self.completed is not None):
            raise ValueError("research work result does not match completion")


class ProcessOneResearchJob:
    """Claim, renew, resolve, execute, store, and finalize no more than one job."""

    __slots__ = ("_worker", "_resolver", "_artifacts")

    def __init__(
        self,
        worker: PersistentResearchWorkerControl,
        resolver: ResearchRunnerResolver,
        artifacts: ArtifactStore,
    ) -> None:
        self._worker = worker
        self._resolver = resolver
        self._artifacts = artifacts

    def __repr__(self) -> str:
        return "ProcessOneResearchJob()"

    def process(self, worker_id: ResearchWorkerId) -> ResearchWorkResult:
        claimed = self._worker.claim(worker_id)
        if claimed is None:
            return ResearchWorkResult(ResearchWorkResultKind.IDLE)

        renewed = self._worker.heartbeat(
            claimed.job_id,
            claimed.revision_id,
            claimed.worker_id,
            claimed.claim_id,
        )
        if renewed is None:
            return ResearchWorkResult(ResearchWorkResultKind.CLAIM_LOST)
        claimed = replace(
            claimed,
            revision_id=renewed.revision_id,
            lease_expires_at=renewed.lease_expires_at,
        )

        try:
            runner: BacktestExecution = self._resolver.resolve(claimed.snapshot)
            summary = execute_local_research(runner, title=claimed.snapshot.title)
        except Exception:
            completed = self._worker.finalize_failure(
                claimed, ResearchJobFailureCode.EXECUTION_FAILED
            )
            if completed is None:
                return ResearchWorkResult(ResearchWorkResultKind.CLAIM_LOST)
            return ResearchWorkResult(ResearchWorkResultKind.FAILED, completed)

        if summary.experiment_id != str(claimed.snapshot.experiment_id):
            completed = self._worker.finalize_failure(
                claimed, ResearchJobFailureCode.EXECUTION_FAILED
            )
            if completed is None:
                return ResearchWorkResult(ResearchWorkResultKind.CLAIM_LOST)
            return ResearchWorkResult(ResearchWorkResultKind.FAILED, completed)

        try:
            content = json.dumps(
                evidence_document(summary),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            opaque_job = hashlib.sha256(
                str(claimed.job_id).encode("utf-8")
            ).hexdigest()
            artifact = self._artifacts.put(
                key=f"research/{opaque_job}/result.json",
                content=content,
                media_type="application/json",
            )
        except Exception:
            raise ResearchJobProcessingUnavailable from None
        completed = self._worker.finalize_success(claimed, summary, artifact)
        if completed is None:
            return ResearchWorkResult(ResearchWorkResultKind.CLAIM_LOST)
        return ResearchWorkResult(ResearchWorkResultKind.SUCCEEDED, completed)
