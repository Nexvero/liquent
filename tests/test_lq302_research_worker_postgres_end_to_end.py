from __future__ import annotations

import hashlib
import multiprocessing
import secrets
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.application.local_csv import LocalCsvMidBreakoutV0Resolver
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    ExperimentId, JobId, ResearchJobAcceptanceId, ResearchJobClaimId,
    ResearchJobRevisionId, ResearchWorkerId, StrategyVersionId, WorkspaceId,
)
from liquent_platform.identity.research_job import ResearchResultArtifactClass
from liquent_platform.identity.session import ResolvedBrowserSession, SessionPrincipal
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.operators.research_worker_composition import compose_research_worker
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.research_artifacts import LocalImmutableResearchArtifactStore


pytestmark = pytest.mark.postgres_integration
FIXTURES = Path(__file__).parent / "fixtures"


def _identifier(kind, prefix: str):
    return kind(f"{prefix}-{secrets.token_hex(16)}")


def _run_one_worker(
    database_url: str,
    data_root: str,
    artifact_root: str,
    worker_name: str,
    start,
    outcomes,
) -> None:
    engine = build_engine(database_url)
    try:
        composition = compose_research_worker(
            engine=engine,
            resolver=LocalCsvMidBreakoutV0Resolver(Path(data_root)),
            artifacts=LocalImmutableResearchArtifactStore(Path(artifact_root)),
            generate_job_id=lambda: _identifier(JobId, "job"),
            generate_revision_id=lambda: _identifier(ResearchJobRevisionId, "revision"),
            generate_claim_id=lambda: _identifier(ResearchJobClaimId, "claim"),
            lease_duration=timedelta(seconds=30),
        )
        start.wait(timeout=20)
        result = composition.processor.process(ResearchWorkerId(worker_name))
        outcomes.put((worker_name, result.kind.value, None))
    except Exception as error:
        outcomes.put((worker_name, None, type(error).__name__))
    finally:
        engine.dispose()


def _snapshot() -> ExperimentSnapshot:
    dataset = FIXTURES / "ohlcv_valid.csv"
    return ExperimentSnapshot(
        ExperimentId("lq302-experiment"), WorkspaceId("lq302-workspace"),
        "LQ-302 PostgreSQL process proof", dataset.name,
        f"sha256:{hashlib.sha256(dataset.read_bytes()).hexdigest()}",
        StrategyVersionId("mid-breakout-v0"),
        freeze_parameters({
            "lookback_bars": 1, "stop_distance_pct": 0.05,
            "min_strength": 0.0, "allow_short": True,
        }),
        freeze_parameters({
            "initial_equity": 1000.0, "max_position_size": 10.0,
            "max_total_exposure": 100.0, "risk_per_trade": 5.0,
            "max_daily_drawdown": 1000.0, "sizing_mode": "absolute",
        }),
        freeze_parameters({"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0}),
    )


def test_two_processes_complete_one_postgresql_job_exactly_once(
    postgres_engine: Engine, postgres_url: str, tmp_path: Path
) -> None:
    actor = UserId("lq302-user")
    workspace = WorkspaceId("lq302-workspace")
    with postgres_engine.begin() as connection:
        connection.execute(text("INSERT INTO identity_users VALUES (:u,'active')"), {"u": b"lq302-user"})
        connection.execute(text("INSERT INTO identity_workspaces VALUES (:w,'active')"), {"w": b"lq302-workspace"})
        connection.execute(text("INSERT INTO workspace_memberships (user_id,workspace_id,status) VALUES (:u,:w,'active')"), {"u": b"lq302-user", "w": b"lq302-workspace"})
        connection.execute(text("INSERT INTO workspace_membership_permissions VALUES (:u,:w,'research:write')"), {"u": b"lq302-user", "w": b"lq302-workspace"})

    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(mode=0o700)
    parent = compose_research_worker(
        engine=postgres_engine,
        resolver=LocalCsvMidBreakoutV0Resolver(FIXTURES),
        artifacts=LocalImmutableResearchArtifactStore(artifact_root),
        generate_job_id=lambda: JobId("lq302-job"),
        generate_revision_id=lambda: _identifier(ResearchJobRevisionId, "revision"),
        generate_claim_id=lambda: _identifier(ResearchJobClaimId, "claim"),
        lease_duration=timedelta(seconds=30),
    )
    session = ResolvedBrowserSession(SessionPrincipal(actor), "lq302-csrf")
    accepted = parent.jobs.control_plane.accept(
        session, "lq302-csrf", ResearchJobAcceptanceId("lq302-acceptance"), _snapshot(),
        ResearchResultArtifactClass.BACKTEST_RESULT_V1,
    )
    assert accepted is not None

    context = multiprocessing.get_context("spawn")
    start = context.Barrier(2)
    outcomes = context.Queue()
    processes = [
        context.Process(target=_run_one_worker, args=(
            postgres_url, str(FIXTURES), str(artifact_root), name, start, outcomes,
        ))
        for name in ("lq302-worker-a", "lq302-worker-b")
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=60)

    assert all(not process.is_alive() for process in processes)
    assert [process.exitcode for process in processes] == [0, 0]
    observed = [outcomes.get(timeout=5) for _ in processes]
    assert not [(name, failure) for name, _, failure in observed if failure]
    assert sorted(kind for _, kind, _ in observed) == ["idle", "succeeded"]

    view = parent.jobs.control_plane.get(session.principal, accepted.job_id)
    assert view is not None and view.status is ResearchJobStatus.SUCCEEDED
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM research_job_claims")).scalar_one() == 1
        outcome = connection.execute(text("SELECT artifact_key,artifact_sha256 FROM research_job_outcomes")).one()
    artifact = artifact_root / outcome.artifact_key
    content = artifact.read_bytes()
    assert hashlib.sha256(content).hexdigest() == outcome.artifact_sha256
