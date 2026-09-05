from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event

from liquent_platform.application.csrf import CsrfValidationFailed
from liquent_platform.application.experiment import ExperimentSnapshot
from liquent_platform.application.persistent_research_jobs import (
    PersistentResearchControlPlane,
    PersistentResearchWorkerControl,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    ExperimentId, JobId, ResearchJobAcceptanceId, ResearchJobClaimId,
    ResearchJobRevisionId, ResearchWorkerId, StrategyVersionId, WorkspaceId,
)
from liquent_platform.identity.research_job import ResearchResultArtifactClass
from liquent_platform.identity.session import ResolvedBrowserSession, SessionPrincipal
from liquent_platform.persistence.research_job_composition import (
    PersistentResearchJobComposition,
    compose_persistent_research_jobs,
)


class Recorder:
    def __init__(self): self.calls = []
    def accept_job(self, *values): self.calls.append(("accept", values)); return None
    def get_job(self, *values): self.calls.append(("get", values)); return None
    def claim_next(self, *values): self.calls.append(("claim", values)); return None
    def heartbeat(self, *values): self.calls.append(("heartbeat", values)); return None


def _snapshot():
    return ExperimentSnapshot(ExperimentId("e"), WorkspaceId("w"), "title",
        "dataset", "fingerprint", StrategyVersionId("s"), (), (), ())


def test_control_plane_validates_csrf_and_passes_only_actor_identity():
    recorder = Recorder()
    control = PersistentResearchControlPlane(recorder, recorder)
    session = ResolvedBrowserSession(SessionPrincipal(UserId("user")), "csrf")
    with pytest.raises(CsrfValidationFailed):
        control.accept(session, "wrong", ResearchJobAcceptanceId("a"), _snapshot(),
            ResearchResultArtifactClass.BACKTEST_RESULT_V1)
    assert recorder.calls == []
    control.accept(session, "csrf", ResearchJobAcceptanceId("a"), _snapshot(),
        ResearchResultArtifactClass.BACKTEST_RESULT_V1)
    assert recorder.calls[0][1][1] == UserId("user")
    assert all("Session" not in type(value).__name__ for value in recorder.calls[0][1])


def test_worker_control_never_receives_session_or_authority_input():
    recorder = Recorder()
    worker = PersistentResearchWorkerControl(recorder, recorder)
    worker_id, claim_id = ResearchWorkerId("worker"), ResearchJobClaimId("claim")
    worker.claim(worker_id)
    worker.heartbeat(JobId("job"), ResearchJobRevisionId("revision"), worker_id, claim_id)
    assert recorder.calls == [
        ("claim", (worker_id,)),
        ("heartbeat", (JobId("job"), ResearchJobRevisionId("revision"), worker_id, claim_id)),
    ]


def test_composition_is_side_effect_free_and_shares_exactly_one_store():
    engine = create_engine("sqlite://")
    connections = []
    event.listen(engine, "connect", lambda *_: connections.append(True))
    composition = compose_persistent_research_jobs(
        engine,
        generate_job_id=lambda: JobId("job"),
        generate_revision_id=lambda: ResearchJobRevisionId("revision"),
        generate_claim_id=lambda: ResearchJobClaimId("claim"),
        lease_duration=timedelta(seconds=30),
        clock=lambda: datetime(2026, 8, 19, tzinfo=timezone.utc),
    )
    assert type(composition) is PersistentResearchJobComposition
    assert repr(composition) == "PersistentResearchJobComposition()"
    assert repr(composition.control_plane) == "PersistentResearchControlPlane()"
    assert repr(composition.worker_control) == "PersistentResearchWorkerControl()"
    assert composition.control_plane._acceptances is composition.store
    assert composition.worker_control._claims is composition.store
    assert connections == []


def test_invalid_lease_fails_before_any_database_access():
    engine = create_engine("sqlite://")
    connections = []
    event.listen(engine, "connect", lambda *_: connections.append(True))
    with pytest.raises(ValueError):
        compose_persistent_research_jobs(
            engine,
            generate_job_id=lambda: JobId("job"),
            generate_revision_id=lambda: ResearchJobRevisionId("revision"),
            generate_claim_id=lambda: ResearchJobClaimId("claim"),
            lease_duration=timedelta(0),
        )
    assert connections == []
