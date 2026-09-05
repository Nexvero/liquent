"""Atomic persistent research-job acceptance, claiming, leases, and lookup."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from sqlalchemy import Engine, text

from liquent_platform.application.experiment import ExperimentSnapshot
from liquent_platform.application.ports import ArtifactReference
from liquent.backtesting.reporting import BacktestExperimentSummary
from liquent_platform.application.evidence import evidence_document
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    ExperimentId, JobId, ResearchJobAcceptanceId, ResearchJobClaimId,
    ResearchJobRevisionId, ResearchWorkerId, StrategyVersionId, WorkspaceId,
)
from liquent_platform.identity.research_job import (
    AcceptedResearchJob, ClaimedResearchJob, CompletedResearchJob,
    RenewedResearchJobLease, ResearchJobFailureCode,
    ResearchJobAcceptanceConflict, ResearchJobView, ResearchResultArtifactClass,
)
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.persistence.identity_errors import ResearchJobStoreUnavailable


def _b(value: object) -> bytes:
    raw = value.value if hasattr(value, "value") else value
    if type(raw) is not str or not raw:
        raise ResearchJobStoreUnavailable
    return raw.encode()


def _s(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ResearchJobStoreUnavailable
    return bytes(value).decode()


def _snapshot_json(snapshot: ExperimentSnapshot) -> str:
    if type(snapshot) is not ExperimentSnapshot:
        raise ResearchJobStoreUnavailable
    return json.dumps({
        "experiment_id": str(snapshot.experiment_id), "workspace_id": str(snapshot.workspace_id),
        "title": snapshot.title, "dataset_ref": snapshot.dataset_ref,
        "dataset_fingerprint": snapshot.dataset_fingerprint,
        "strategy_version_id": str(snapshot.strategy_version_id),
        "strategy_parameters": snapshot.strategy_parameters,
        "risk_parameters": snapshot.risk_parameters, "cost_parameters": snapshot.cost_parameters,
    }, sort_keys=True, separators=(",", ":"))


def _snapshot(raw: str) -> ExperimentSnapshot:
    data = json.loads(raw)
    return ExperimentSnapshot(
        ExperimentId(data["experiment_id"]), WorkspaceId(data["workspace_id"]),
        data["title"], data["dataset_ref"], data["dataset_fingerprint"],
        StrategyVersionId(data["strategy_version_id"]),
        tuple(tuple(v) for v in data["strategy_parameters"]),
        tuple(tuple(v) for v in data["risk_parameters"]),
        tuple(tuple(v) for v in data["cost_parameters"]),
    )


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ResearchJobStoreUnavailable
    return value


def _stored_utc(value: object) -> datetime:
    if type(value) is str:
        value = datetime.fromisoformat(value)
    if type(value) is not datetime:
        raise ResearchJobStoreUnavailable
    return value.replace(tzinfo=value.tzinfo or timezone.utc)


class DatabaseResearchJobs:
    __slots__ = ("_engine", "_job_id", "_revision_id", "_claim_id", "_clock", "_lease")

    def __init__(self, engine: Engine, *, generate_job_id: Callable[[], JobId],
                 generate_revision_id: Callable[[], ResearchJobRevisionId],
                 generate_claim_id: Callable[[], ResearchJobClaimId],
                 clock: Callable[[], datetime], lease_duration: timedelta) -> None:
        if type(lease_duration) is not timedelta or lease_duration <= timedelta(0):
            raise ValueError("lease duration must be positive")
        self._engine, self._job_id, self._revision_id = engine, generate_job_id, generate_revision_id
        self._claim_id, self._clock, self._lease = generate_claim_id, clock, lease_duration

    def __repr__(self) -> str:
        return "DatabaseResearchJobs()"

    def accept_job(self, acceptance_id, actor_user_id, snapshot, artifact_class):
        try:
            payload, now = _snapshot_json(snapshot), _utc(self._clock())
            values = {"acceptance": _b(acceptance_id), "actor": _b(actor_user_id),
                      "workspace": _b(snapshot.workspace_id), "snapshot": payload,
                      "artifact": artifact_class.value}
            with self._engine.begin() as c:
                if c.dialect.name == "postgresql":
                    c.execute(text("LOCK TABLE research_job_acceptances IN SHARE ROW EXCLUSIVE MODE"))
                elif c.dialect.name != "sqlite": raise ResearchJobStoreUnavailable
                old = c.execute(text("SELECT j.* FROM research_job_acceptances a JOIN research_jobs j ON j.job_id=a.job_id WHERE a.acceptance_id=:acceptance"), values).mappings().one_or_none()
                if old:
                    if old["actor_user_id"] != values["actor"] or old["snapshot_json"] != payload or old["artifact_class"] != values["artifact"]:
                        return ResearchJobAcceptanceConflict()
                    return self._accepted(acceptance_id, old)
                allowed = c.execute(text("SELECT 1 FROM identity_users u JOIN identity_workspaces w ON w.workspace_id=:workspace JOIN workspace_memberships m ON m.user_id=u.user_id AND m.workspace_id=w.workspace_id JOIN workspace_membership_permissions p ON p.user_id=m.user_id AND p.workspace_id=m.workspace_id WHERE u.user_id=:actor AND u.status='active' AND w.status='active' AND m.status='active' AND p.permission='research:write'"), values).first()
                if not allowed: return None
                job, revision = self._job_id(), self._revision_id()
                values.update(job=_b(job), revision=_b(revision), now=now, status="queued")
                c.execute(text("INSERT INTO research_jobs VALUES (:job,:revision,:actor,:workspace,:snapshot,:artifact,:status,:now,:now)"), values)
                c.execute(text("INSERT INTO research_job_acceptances VALUES (:acceptance,:job)"), values)
                return AcceptedResearchJob(acceptance_id, job, revision, actor_user_id, snapshot, artifact_class, now)
        except ResearchJobStoreUnavailable: raise
        except Exception: raise ResearchJobStoreUnavailable from None

    def _accepted(self, acceptance_id, row):
        return AcceptedResearchJob(acceptance_id, JobId(_s(row["job_id"])), ResearchJobRevisionId(_s(row["revision_id"])), UserId(_s(row["actor_user_id"])), _snapshot(row["snapshot_json"]), ResearchResultArtifactClass(row["artifact_class"]), _stored_utc(row["accepted_at"]))

    def claim_next(self, worker_id):
        try:
            with self._engine.begin() as c:
                dialect = c.dialect.name
                if dialect not in ("sqlite", "postgresql"): raise ResearchJobStoreUnavailable
                suffix = " FOR UPDATE SKIP LOCKED" if dialect == "postgresql" else ""
                while True:
                    row = c.execute(text("SELECT * FROM research_jobs WHERE status='queued' ORDER BY accepted_at,job_id LIMIT 1" + suffix)).mappings().one_or_none()
                    if not row: return None
                    authority = c.execute(text("SELECT 1 FROM identity_users u JOIN identity_workspaces w ON w.workspace_id=:w JOIN workspace_memberships m ON m.user_id=u.user_id AND m.workspace_id=w.workspace_id JOIN workspace_membership_permissions p ON p.user_id=m.user_id AND p.workspace_id=m.workspace_id WHERE u.user_id=:u AND u.status='active' AND w.status='active' AND m.status='active' AND p.permission='research:write'"), {"u": row["actor_user_id"], "w": row["workspace_id"]}).first()
                    revision, now = self._revision_id(), _utc(self._clock())
                    if not authority:
                        c.execute(text("UPDATE research_jobs SET status='invalidated',revision_id=:r,updated_at=:n WHERE job_id=:j"), {"r": _b(revision), "n": now, "j": row["job_id"]}); continue
                    claim, expiry = self._claim_id(), now + self._lease
                    c.execute(text("UPDATE research_jobs SET status='running',revision_id=:r,updated_at=:n WHERE job_id=:j AND status='queued'"), {"r": _b(revision), "n": now, "j": row["job_id"]})
                    c.execute(text("INSERT INTO research_job_claims VALUES (:j,:c,:w,:n,:e)"), {"j": row["job_id"], "c": _b(claim), "w": _b(worker_id), "n": now, "e": expiry})
                    return ClaimedResearchJob(JobId(_s(row["job_id"])), revision, UserId(_s(row["actor_user_id"])), WorkspaceId(_s(row["workspace_id"])), worker_id, claim, _snapshot(row["snapshot_json"]), ResearchResultArtifactClass(row["artifact_class"]), now, expiry)
        except ResearchJobStoreUnavailable: raise
        except Exception: raise ResearchJobStoreUnavailable from None

    def heartbeat(self, job_id, expected_revision, worker_id, claim_id):
        try:
            now = _utc(self._clock())
            with self._engine.begin() as c:
                row = c.execute(text("SELECT lease_expires_at FROM research_jobs j JOIN research_job_claims c ON c.job_id=j.job_id WHERE j.job_id=:j AND j.revision_id=:r AND j.status='running' AND c.worker_id=:w AND c.claim_id=:c"), {"j": _b(job_id), "r": _b(expected_revision), "w": _b(worker_id), "c": _b(claim_id)}).one_or_none()
                if not row: return None
                expiry = _stored_utc(row.lease_expires_at)
                if expiry <= now: return None
                revision = self._revision_id()
                new_expiry = now + self._lease
                c.execute(text("UPDATE research_jobs SET revision_id=:nr,updated_at=:n WHERE job_id=:j"), {"nr": _b(revision), "n": now, "j": _b(job_id)})
                c.execute(text("UPDATE research_job_claims SET lease_expires_at=:e WHERE job_id=:j"), {"e": new_expiry, "j": _b(job_id)})
                return RenewedResearchJobLease(job_id, revision, worker_id, claim_id, new_expiry)
        except ResearchJobStoreUnavailable: raise
        except Exception: raise ResearchJobStoreUnavailable from None

    def _current_claim(self, c, job_id, expected_revision, worker_id, claim_id, now):
        row = c.execute(text("SELECT j.snapshot_json,c.lease_expires_at FROM research_jobs j JOIN research_job_claims c ON c.job_id=j.job_id WHERE j.job_id=:j AND j.revision_id=:r AND j.status='running' AND c.worker_id=:w AND c.claim_id=:c"), {"j": _b(job_id), "r": _b(expected_revision), "w": _b(worker_id), "c": _b(claim_id)}).mappings().one_or_none()
        if row is None or _stored_utc(row["lease_expires_at"]) <= now:
            return None
        return row

    def finalize_success(self, job_id, expected_revision, worker_id, claim_id,
                         summary, artifact):
        try:
            if type(summary) is not BacktestExperimentSummary or type(artifact) is not ArtifactReference:
                raise ResearchJobStoreUnavailable
            if (type(artifact.key) is not str or not artifact.key or
                type(artifact.sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", artifact.sha256) or
                artifact.media_type != "application/json" or
                type(artifact.size_bytes) is not int or artifact.size_bytes < 1):
                raise ResearchJobStoreUnavailable
            now = _utc(self._clock())
            with self._engine.begin() as c:
                row = self._current_claim(c, job_id, expected_revision, worker_id, claim_id, now)
                if row is None: return None
                snapshot = _snapshot(row["snapshot_json"])
                if summary.experiment_id != str(snapshot.experiment_id):
                    return None
                revision = self._revision_id()
                payload = json.dumps(evidence_document(summary), sort_keys=True, separators=(",", ":"), allow_nan=False)
                c.execute(text("INSERT INTO research_job_outcomes VALUES (:j,'succeeded',:s,:k,:h,:m,:z,NULL,:n)"), {"j": _b(job_id), "s": payload, "k": artifact.key, "h": artifact.sha256, "m": artifact.media_type, "z": artifact.size_bytes, "n": now})
                c.execute(text("UPDATE research_jobs SET status='succeeded',revision_id=:r,updated_at=:n WHERE job_id=:j"), {"r": _b(revision), "n": now, "j": _b(job_id)})
                return CompletedResearchJob(job_id, revision, ResearchJobStatus.SUCCEEDED, now, summary, artifact)
        except ResearchJobStoreUnavailable: raise
        except Exception: raise ResearchJobStoreUnavailable from None

    def finalize_failure(self, job_id, expected_revision, worker_id, claim_id,
                         failure_code):
        try:
            if type(failure_code) is not ResearchJobFailureCode:
                raise ResearchJobStoreUnavailable
            now = _utc(self._clock())
            with self._engine.begin() as c:
                if self._current_claim(c, job_id, expected_revision, worker_id, claim_id, now) is None:
                    return None
                revision = self._revision_id()
                c.execute(text("INSERT INTO research_job_outcomes VALUES (:j,'failed',NULL,NULL,NULL,NULL,NULL,:f,:n)"), {"j": _b(job_id), "f": failure_code.value, "n": now})
                c.execute(text("UPDATE research_jobs SET status='failed',revision_id=:r,updated_at=:n WHERE job_id=:j"), {"r": _b(revision), "n": now, "j": _b(job_id)})
                return CompletedResearchJob(job_id, revision, ResearchJobStatus.FAILED, now, failure_code=failure_code)
        except ResearchJobStoreUnavailable: raise
        except Exception: raise ResearchJobStoreUnavailable from None

    def get_job(self, actor_user_id, job_id):
        try:
            with self._engine.connect() as c:
                row = c.execute(text("SELECT j.* FROM research_jobs j JOIN identity_users u ON u.user_id=:u AND u.status='active' JOIN identity_workspaces w ON w.workspace_id=j.workspace_id AND w.status='active' JOIN workspace_memberships m ON m.user_id=:u AND m.workspace_id=j.workspace_id AND m.status='active' JOIN workspace_membership_permissions p ON p.user_id=:u AND p.workspace_id=j.workspace_id AND p.permission IN ('research:read','research:write') WHERE j.job_id=:j"), {"u": _b(actor_user_id), "j": _b(job_id)}).mappings().one_or_none()
            if not row: return None
            accepted = _stored_utc(row["accepted_at"])
            updated = _stored_utc(row["updated_at"])
            return ResearchJobView(job_id, ResearchJobRevisionId(_s(row["revision_id"])), WorkspaceId(_s(row["workspace_id"])), ResearchJobStatus(row["status"]), accepted, updated)
        except ResearchJobStoreUnavailable: raise
        except Exception: raise ResearchJobStoreUnavailable from None
