import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from liquent.backtesting.runner import BacktestResult
from liquent_platform.application.ports import ArtifactReference
from liquent_platform.application.process_research_job import (
    ProcessOneResearchJob, ResearchJobProcessingUnavailable,
    ResearchWorkResultKind,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    ExperimentId, JobId, ResearchJobClaimId, ResearchJobRevisionId,
    ResearchWorkerId, StrategyVersionId, WorkspaceId,
)
from liquent_platform.identity.research_job import (
    ClaimedResearchJob, CompletedResearchJob, RenewedResearchJobLease,
    ResearchResultArtifactClass,
)
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.application.experiment import ExperimentSnapshot


NOW = datetime(2026, 8, 19, tzinfo=timezone.utc)


def _claim():
    snapshot = ExperimentSnapshot(ExperimentId("experiment"), WorkspaceId("workspace"),
        "title", "dataset", "fingerprint", StrategyVersionId("strategy"), (), (), ())
    return ClaimedResearchJob(
        JobId("job-secret"), ResearchJobRevisionId("r1"), UserId("user"),
        WorkspaceId("workspace"), ResearchWorkerId("worker"),
        ResearchJobClaimId("claim"), snapshot,
        ResearchResultArtifactClass.BACKTEST_RESULT_V1,
        NOW, NOW + timedelta(seconds=30),
    )


class Worker:
    def __init__(self, claim=_claim(), renew=True):
        self.claimed, self.renew, self.calls = claim, renew, []
    def claim(self, worker): self.calls.append("claim"); return self.claimed
    def heartbeat(self, *args):
        self.calls.append("heartbeat")
        if not self.renew: return None
        return RenewedResearchJobLease(args[0], ResearchJobRevisionId("r2"), args[2], args[3], NOW + timedelta(seconds=60))
    def finalize_success(self, claim, summary, artifact):
        self.calls.append("success")
        return CompletedResearchJob(claim.job_id, ResearchJobRevisionId("r3"), ResearchJobStatus.SUCCEEDED, NOW, summary, artifact)
    def finalize_failure(self, claim, code):
        self.calls.append("failure")
        return CompletedResearchJob(claim.job_id, ResearchJobRevisionId("r3"), ResearchJobStatus.FAILED, NOW, failure_code=code)


class Runner:
    def run(self):
        return BacktestResult("experiment", 0, 0, 0, 100.0, 100.0, (100.0,),
            {"return": float("nan")}, (), {"strategy": "controlled", "sizing_mode": "absolute",
            "live_execution": False, "network_calls": False, "paper_trading": False})


class Resolver:
    def __init__(self, runner=Runner()): self.runner, self.calls = runner, 0
    def resolve(self, snapshot): self.calls += 1; return self.runner


class Artifacts:
    def __init__(self, broken=False): self.values, self.broken = [], broken
    def put(self, *, key, content, media_type):
        if self.broken: raise RuntimeError("private artifact fault")
        self.values.append((key, content, media_type))
        return ArtifactReference(key, hashlib.sha256(content).hexdigest(), media_type, len(content))


def test_idle_and_lost_initial_heartbeat_execute_nothing():
    resolver, artifacts = Resolver(), Artifacts()
    idle = ProcessOneResearchJob(Worker(None), resolver, artifacts).process(ResearchWorkerId("worker"))
    lost_worker = Worker(renew=False)
    lost = ProcessOneResearchJob(lost_worker, resolver, artifacts).process(ResearchWorkerId("worker"))
    assert idle.kind is ResearchWorkResultKind.IDLE
    assert lost.kind is ResearchWorkResultKind.CLAIM_LOST
    assert resolver.calls == 0 and artifacts.values == []
    assert lost_worker.calls == ["claim", "heartbeat"]


def test_success_renews_before_execution_writes_canonical_artifact_then_finalizes():
    worker, resolver, artifacts = Worker(), Resolver(), Artifacts()
    result = ProcessOneResearchJob(worker, resolver, artifacts).process(ResearchWorkerId("worker"))
    assert result.kind is ResearchWorkResultKind.SUCCEEDED
    assert worker.calls == ["claim", "heartbeat", "success"]
    key, content, media = artifacts.values[0]
    assert "job-secret" not in key and key.endswith("/result.json")
    assert media == "application/json"
    assert json.loads(content)["metrics"]["return"] is None


def test_runner_failure_finalizes_detail_free_without_artifact():
    class Broken:
        def run(self): raise RuntimeError("private runner detail")
    worker, artifacts = Worker(), Artifacts()
    result = ProcessOneResearchJob(worker, Resolver(Broken()), artifacts).process(ResearchWorkerId("worker"))
    assert result.kind is ResearchWorkResultKind.FAILED
    assert worker.calls == ["claim", "heartbeat", "failure"]
    assert artifacts.values == []


def test_artifact_failure_is_technical_and_does_not_finalize():
    worker = Worker()
    with pytest.raises(ResearchJobProcessingUnavailable) as caught:
        ProcessOneResearchJob(worker, Resolver(), Artifacts(True)).process(ResearchWorkerId("worker"))
    assert str(caught.value) == "research_job_processing_unavailable"
    assert caught.value.__cause__ is None
    assert worker.calls == ["claim", "heartbeat"]
