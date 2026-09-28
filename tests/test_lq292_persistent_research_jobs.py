from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    ExperimentId, JobId, ResearchJobAcceptanceId, ResearchJobClaimId,
    ResearchJobRevisionId, ResearchWorkerId, StrategyVersionId, WorkspaceId,
)
from liquent_platform.identity.research_job import ResearchResultArtifactClass
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.research_jobs import DatabaseResearchJobs


def _snapshot():
    return ExperimentSnapshot(ExperimentId("e"), WorkspaceId("w"), "title", "data",
        "hash", StrategyVersionId("s"), freeze_parameters({"x": 1}), (), ())


def _store(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'jobs.db'}")
    upgrade_to_head(str(engine.url))
    values = iter([ResearchJobRevisionId("r1"), ResearchJobRevisionId("r2"), ResearchJobRevisionId("r3")])
    claims = iter([ResearchJobClaimId("c1")])
    now = datetime(2026, 8, 19, tzinfo=timezone.utc)
    store = DatabaseResearchJobs(engine, generate_job_id=lambda: JobId("j1"),
        generate_revision_id=lambda: next(values), generate_claim_id=lambda: next(claims),
        clock=lambda: now, lease_duration=timedelta(seconds=30))
    with engine.begin() as c:
        c.execute(text("INSERT INTO identity_users VALUES (:u,'active')"), {"u": b"u"})
        c.execute(text("INSERT INTO identity_workspaces VALUES (:w,'active')"), {"w": b"w"})
        c.execute(text("INSERT INTO workspace_memberships (user_id,workspace_id,status) VALUES (:u,:w,'active')"), {"u": b"u", "w": b"w"})
        c.execute(text("INSERT INTO workspace_membership_permissions VALUES (:u,:w,'research:write')"), {"u": b"u", "w": b"w"})
    return engine, store


def test_accept_retry_claim_heartbeat_lookup_and_revocation(tmp_path):
    engine, store = _store(tmp_path)
    request, actor, snapshot = ResearchJobAcceptanceId("a"), UserId("u"), _snapshot()
    accepted = store.accept_job(request, actor, snapshot, ResearchResultArtifactClass.BACKTEST_RESULT_V1)
    assert accepted == store.accept_job(request, actor, snapshot, ResearchResultArtifactClass.BACKTEST_RESULT_V1)
    claimed = store.claim_next(ResearchWorkerId("worker"))
    assert claimed is not None and store.claim_next(ResearchWorkerId("other")) is None
    renewed = store.heartbeat(claimed.job_id, claimed.revision_id, claimed.worker_id, claimed.claim_id)
    assert renewed is not None
    assert store.heartbeat(claimed.job_id, claimed.revision_id, claimed.worker_id, claimed.claim_id) is None
    assert store.get_job(actor, accepted.job_id) is not None
    with engine.begin() as c:
        c.execute(text("DELETE FROM workspace_membership_permissions"))
    assert store.get_job(actor, accepted.job_id) is None


def test_acceptance_without_current_write_authority_is_neutral(tmp_path):
    _, store = _store(tmp_path)
    assert store.accept_job(ResearchJobAcceptanceId("a"), UserId("other"), _snapshot(),
        ResearchResultArtifactClass.BACKTEST_RESULT_V1) is None
