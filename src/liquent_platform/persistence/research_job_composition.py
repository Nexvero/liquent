"""Side-effect-free composition of persistent research-job capabilities."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from liquent_platform.application.persistent_research_jobs import (
    PersistentResearchControlPlane,
    PersistentResearchWorkerControl,
)
from liquent_platform.identity.research import (
    JobId,
    ResearchJobClaimId,
    ResearchJobRevisionId,
)
from liquent_platform.persistence.research_jobs import DatabaseResearchJobs


@dataclass(frozen=True, slots=True)
class PersistentResearchJobComposition:
    control_plane: PersistentResearchControlPlane
    worker_control: PersistentResearchWorkerControl
    store: DatabaseResearchJobs

    def __repr__(self) -> str:
        return "PersistentResearchJobComposition()"


def compose_persistent_research_jobs(
    engine: Engine,
    *,
    generate_job_id: Callable[[], JobId],
    generate_revision_id: Callable[[], ResearchJobRevisionId],
    generate_claim_id: Callable[[], ResearchJobClaimId],
    lease_duration: timedelta,
    clock: Callable[[], datetime] | None = None,
) -> PersistentResearchJobComposition:
    """Wire one shared store without database access or process startup."""

    store = DatabaseResearchJobs(
        engine,
        generate_job_id=generate_job_id,
        generate_revision_id=generate_revision_id,
        generate_claim_id=generate_claim_id,
        clock=clock or (lambda: datetime.now(UTC)),
        lease_duration=lease_duration,
    )
    return PersistentResearchJobComposition(
        PersistentResearchControlPlane(store, store),
        PersistentResearchWorkerControl(store, store, store),
        store,
    )
