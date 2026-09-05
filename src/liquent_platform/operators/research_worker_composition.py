"""Side-effect-free composition of one controlled research-worker path."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Engine

from liquent_platform.application.ports import ArtifactStore
from liquent_platform.application.process_research_job import ProcessOneResearchJob
from liquent_platform.application.start_research import ResearchRunnerResolver
from liquent_platform.identity.research import (
    JobId,
    ResearchJobClaimId,
    ResearchJobRevisionId,
)
from liquent_platform.persistence.research_job_composition import (
    PersistentResearchJobComposition,
    compose_persistent_research_jobs,
)


@dataclass(frozen=True, slots=True)
class ResearchWorkerComposition:
    jobs: PersistentResearchJobComposition
    processor: ProcessOneResearchJob

    def __repr__(self) -> str:
        return "ResearchWorkerComposition()"


def compose_research_worker(
    *,
    engine: Engine,
    resolver: ResearchRunnerResolver,
    artifacts: ArtifactStore,
    generate_job_id: Callable[[], JobId],
    generate_revision_id: Callable[[], ResearchJobRevisionId],
    generate_claim_id: Callable[[], ResearchJobClaimId],
    lease_duration: timedelta,
    clock: Callable[[], datetime] | None = None,
) -> ResearchWorkerComposition:
    """Build one shared persistent control plane and one single-job processor.

    Every resource remains externally owned. Construction invokes none of the
    supplied capabilities and performs no database or artifact access.
    """

    jobs = compose_persistent_research_jobs(
        engine,
        generate_job_id=generate_job_id,
        generate_revision_id=generate_revision_id,
        generate_claim_id=generate_claim_id,
        lease_duration=lease_duration,
        clock=clock,
    )
    processor = ProcessOneResearchJob(jobs.worker_control, resolver, artifacts)
    return ResearchWorkerComposition(jobs, processor)
