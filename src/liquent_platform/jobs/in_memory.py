"""Synchronous in-memory research job for the first product slice."""

from __future__ import annotations

from dataclasses import dataclass

from liquent.backtesting.reporting import BacktestExperimentSummary
from liquent_platform.application.research import BacktestExecution, execute_local_research
from liquent_platform.identity.research import ExperimentId, JobId
from liquent_platform.jobs.lifecycle import ResearchJobStatus, transition


@dataclass
class InMemoryResearchJob:
    """One already-validated research job; intentionally not persistent."""

    job_id: JobId
    experiment_id: ExperimentId
    title: str
    status: ResearchJobStatus = ResearchJobStatus.READY
    evidence: BacktestExperimentSummary | None = None
    error_code: str | None = None

    def execute(self, runner: BacktestExecution) -> None:
        """Run synchronously and retain either evidence or a neutral failure."""

        self.status = transition(self.status, ResearchJobStatus.QUEUED)
        self.status = transition(self.status, ResearchJobStatus.RUNNING)
        try:
            self.evidence = execute_local_research(runner, title=self.title)
        except Exception:
            self.error_code = "execution_failed"
            self.status = transition(self.status, ResearchJobStatus.FAILED)
            return
        self.status = transition(self.status, ResearchJobStatus.SUCCEEDED)


class InMemoryResearchJobs:
    """Minimal process-local lookup; intentionally no repository abstraction."""

    def __init__(self) -> None:
        self._jobs: dict[JobId, InMemoryResearchJob] = {}

    def add(self, job: InMemoryResearchJob) -> None:
        if job.job_id in self._jobs:
            raise ValueError(f"research job already exists: {job.job_id}")
        self._jobs[job.job_id] = job

    def get(self, job_id: JobId) -> InMemoryResearchJob:
        try:
            return self._jobs[job_id]
        except KeyError:
            raise KeyError(f"research job not found: {job_id}") from None
