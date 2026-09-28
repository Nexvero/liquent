from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from liquent.backtesting.reporting import BacktestExperimentSummary
from liquent_platform.application.ports import ArtifactReference
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    JobId, ResearchJobAcceptanceId, ResearchJobClaimId,
    ResearchJobRevisionId, ResearchWorkerId,
)
from liquent_platform.identity.research_job import (
    ResearchJobFailureCode, ResearchResultArtifactClass,
)
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.persistence.research_jobs import DatabaseResearchJobs
from test_lq292_persistent_research_jobs import _snapshot, _store


def _summary():
    return BacktestExperimentSummary(
        "e", "title", "strategy", 100.0, 101.0, 1, 1, 0,
        {"return": 0.01}, {"live_execution": False}, ("descriptive",),
        {"live_execution": False, "network_calls": False, "paper_trading": False},
    )


def _prepared(tmp_path):
    engine, original = _store(tmp_path)
    revisions = iter((ResearchJobRevisionId("accept"), ResearchJobRevisionId("claim"), ResearchJobRevisionId("final")))
    store = DatabaseResearchJobs(
        engine, generate_job_id=lambda: JobId("job-final"),
        generate_revision_id=lambda: next(revisions),
        generate_claim_id=lambda: ResearchJobClaimId("claim-final"),
        clock=lambda: datetime(2026, 8, 19, tzinfo=timezone.utc),
        lease_duration=timedelta(seconds=30),
    )
    accepted = store.accept_job(ResearchJobAcceptanceId("accept-final"), UserId("u"),
        _snapshot(), ResearchResultArtifactClass.BACKTEST_RESULT_V1)
    claimed = store.claim_next(ResearchWorkerId("worker-final"))
    assert accepted is not None and claimed is not None
    return engine, store, claimed


def test_success_is_atomic_claim_bound_and_stale_retry_is_neutral(tmp_path):
    engine, store, claimed = _prepared(tmp_path)
    artifact = ArtifactReference("research/job-final/result.json", "a" * 64,
                                 "application/json", 128)
    completed = store.finalize_success(
        claimed.job_id, claimed.revision_id, claimed.worker_id, claimed.claim_id,
        _summary(), artifact,
    )
    assert completed is not None and completed.status is ResearchJobStatus.SUCCEEDED
    assert store.finalize_success(
        claimed.job_id, claimed.revision_id, claimed.worker_id, claimed.claim_id,
        _summary(), artifact,
    ) is None
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM research_job_outcomes")) == 1
        assert connection.scalar(text("SELECT status FROM research_jobs")) == "succeeded"


def test_failure_is_detail_poor_and_terminal(tmp_path):
    engine, store, claimed = _prepared(tmp_path)
    completed = store.finalize_failure(
        claimed.job_id, claimed.revision_id, claimed.worker_id, claimed.claim_id,
        ResearchJobFailureCode.EXECUTION_FAILED,
    )
    assert completed is not None and completed.status is ResearchJobStatus.FAILED
    assert completed.summary is None and completed.artifact is None
    with engine.connect() as connection:
        row = connection.execute(text("SELECT kind,failure_code,summary_json FROM research_job_outcomes")).one()
        assert tuple(row) == ("failed", "execution_failed", None)


def test_wrong_claim_and_expired_lease_cannot_finalize(tmp_path):
    engine, store, claimed = _prepared(tmp_path)
    assert store.finalize_failure(
        claimed.job_id, claimed.revision_id, claimed.worker_id,
        ResearchJobClaimId("wrong"), ResearchJobFailureCode.EXECUTION_FAILED,
    ) is None
    with engine.begin() as connection:
        connection.execute(text("UPDATE research_job_claims SET lease_expires_at=:past"),
                           {"past": datetime(2026, 8, 18, tzinfo=timezone.utc)})
    assert store.finalize_failure(
        claimed.job_id, claimed.revision_id, claimed.worker_id, claimed.claim_id,
        ResearchJobFailureCode.EXECUTION_FAILED,
    ) is None
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM research_job_outcomes")) == 0
        assert connection.scalar(text("SELECT status FROM research_jobs")) == "running"
