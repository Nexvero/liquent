"""Minimal orchestration for starting one validated research job."""

from typing import Protocol

from liquent_platform.application.experiment import ExperimentSnapshot
from liquent_platform.application.research import BacktestExecution
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs


class ResearchRunnerResolver(Protocol):
    """Resolve one validated snapshot without executing it."""

    def resolve(self, snapshot: ExperimentSnapshot) -> BacktestExecution: ...


def start_research_job(
    job: InMemoryResearchJob,
    runner: BacktestExecution,
    jobs: InMemoryResearchJobs,
) -> InMemoryResearchJob:
    """Register before execution so every accepted outcome remains observable."""

    jobs.add(job)
    job.execute(runner)
    return job


def resolve_and_start_research_job(
    job: InMemoryResearchJob,
    resolver: ResearchRunnerResolver,
    jobs: InMemoryResearchJobs,
) -> InMemoryResearchJob:
    """Resolve inputs first, then use the existing observable start path."""

    runner = resolver.resolve(job.snapshot)
    return start_research_job(job, runner, jobs)
