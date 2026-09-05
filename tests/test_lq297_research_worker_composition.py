from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event

from liquent_platform.application.process_research_job import ProcessOneResearchJob
from liquent_platform.identity.research import (
    JobId, ResearchJobClaimId, ResearchJobRevisionId,
)
from liquent_platform.operators.research_worker_composition import (
    ResearchWorkerComposition, compose_research_worker,
)


class UntouchedResolver:
    def __init__(self): self.calls = 0
    def resolve(self, _): self.calls += 1; raise AssertionError("resolver called")


class UntouchedArtifacts:
    def __init__(self): self.calls = 0
    def put(self, **_): self.calls += 1; raise AssertionError("artifact put called")
    def get(self, _): self.calls += 1; raise AssertionError("artifact get called")


def test_composition_performs_no_database_clock_generator_resolver_or_artifact_io():
    engine = create_engine("sqlite://")
    connections, generated, clock_reads = [], [], []
    event.listen(engine, "connect", lambda *_: connections.append(True))
    resolver, artifacts = UntouchedResolver(), UntouchedArtifacts()

    def forbidden_generator():
        generated.append(True)
        raise AssertionError("generator called")

    def forbidden_clock():
        clock_reads.append(True)
        raise AssertionError("clock called")

    composition = compose_research_worker(
        engine=engine, resolver=resolver, artifacts=artifacts,
        generate_job_id=forbidden_generator,
        generate_revision_id=forbidden_generator,
        generate_claim_id=forbidden_generator,
        lease_duration=timedelta(seconds=30), clock=forbidden_clock,
    )
    assert type(composition) is ResearchWorkerComposition
    assert repr(composition) == "ResearchWorkerComposition()"
    assert type(composition.processor) is ProcessOneResearchJob
    assert connections == generated == clock_reads == []
    assert resolver.calls == artifacts.calls == 0


def test_exactly_one_store_is_shared_by_browser_worker_and_processor():
    composition = compose_research_worker(
        engine=create_engine("sqlite://"), resolver=UntouchedResolver(),
        artifacts=UntouchedArtifacts(), generate_job_id=lambda: JobId("job"),
        generate_revision_id=lambda: ResearchJobRevisionId("revision"),
        generate_claim_id=lambda: ResearchJobClaimId("claim"),
        lease_duration=timedelta(seconds=30),
        clock=lambda: datetime(2026, 8, 19, tzinfo=timezone.utc),
    )
    store = composition.jobs.store
    assert composition.jobs.control_plane._acceptances is store
    assert composition.jobs.control_plane._jobs is store
    assert composition.jobs.worker_control._claims is store
    assert composition.jobs.worker_control._heartbeats is store
    assert composition.jobs.worker_control._finalization is store
    assert composition.processor._worker is composition.jobs.worker_control


@pytest.mark.parametrize("duration", [timedelta(0), timedelta(seconds=-1)])
def test_invalid_lease_fails_before_resource_access(duration):
    engine = create_engine("sqlite://")
    connections = []
    event.listen(engine, "connect", lambda *_: connections.append(True))
    with pytest.raises(ValueError, match="lease duration must be positive"):
        compose_research_worker(
            engine=engine, resolver=UntouchedResolver(), artifacts=UntouchedArtifacts(),
            generate_job_id=lambda: JobId("job"),
            generate_revision_id=lambda: ResearchJobRevisionId("revision"),
            generate_claim_id=lambda: ResearchJobClaimId("claim"),
            lease_duration=duration,
        )
    assert connections == []


def test_composition_does_not_own_or_close_injected_resources():
    engine = create_engine("sqlite://")
    composition = compose_research_worker(
        engine=engine, resolver=UntouchedResolver(), artifacts=UntouchedArtifacts(),
        generate_job_id=lambda: JobId("job"),
        generate_revision_id=lambda: ResearchJobRevisionId("revision"),
        generate_claim_id=lambda: ResearchJobClaimId("claim"),
        lease_duration=timedelta(seconds=30),
    )
    assert not hasattr(composition, "close")
    with engine.connect() as connection:
        assert connection.closed is False
