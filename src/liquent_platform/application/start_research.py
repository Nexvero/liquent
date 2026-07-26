"""Minimal orchestration for starting one already-resolved research job."""

from liquent_platform.application.research import BacktestExecution
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs


def start_research_job(
    job: InMemoryResearchJob,
    runner: BacktestExecution,
    jobs: InMemoryResearchJobs,
) -> InMemoryResearchJob:
    """Register before execution so every accepted outcome remains observable."""

    jobs.add(job)
    job.execute(runner)
    return job
