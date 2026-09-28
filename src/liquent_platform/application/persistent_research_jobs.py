"""Controlled application boundaries for persistent research jobs."""

from __future__ import annotations

from liquent_platform.application.csrf import require_valid_csrf_token
from liquent_platform.application.experiment import ExperimentSnapshot
from liquent_platform.identity.ports import (
    AuthorizedResearchJobAcceptance,
    AuthorizedResearchJobLookup,
    ResearchJobClaim,
    ResearchJobHeartbeat,
    ResearchJobFinalization,
)
from liquent_platform.identity.research import (
    JobId,
    ResearchJobAcceptanceId,
    ResearchJobClaimId,
    ResearchJobRevisionId,
    ResearchWorkerId,
)
from liquent_platform.identity.research_job import (
    AcceptedResearchJob,
    ClaimedResearchJob,
    CompletedResearchJob,
    RenewedResearchJobLease,
    ResearchJobAcceptanceConflict,
    ResearchJobFailureCode,
    ResearchJobView,
    ResearchResultArtifactClass,
)
from liquent_platform.identity.session import ResolvedBrowserSession, SessionPrincipal


class PersistentResearchControlPlane:
    """Submit and read jobs without resolving or executing a runner."""

    __slots__ = ("_acceptances", "_jobs")

    def __init__(
        self,
        acceptances: AuthorizedResearchJobAcceptance,
        jobs: AuthorizedResearchJobLookup,
    ) -> None:
        self._acceptances = acceptances
        self._jobs = jobs

    def __repr__(self) -> str:
        return "PersistentResearchControlPlane()"

    def accept(
        self,
        session: ResolvedBrowserSession,
        presented_csrf_token: str | None,
        acceptance_id: ResearchJobAcceptanceId,
        snapshot: ExperimentSnapshot,
        artifact_class: ResearchResultArtifactClass,
    ) -> AcceptedResearchJob | ResearchJobAcceptanceConflict | None:
        require_valid_csrf_token(
            session.expected_csrf_token, presented_csrf_token
        )
        return self._acceptances.accept_job(
            acceptance_id,
            session.principal.user_id,
            snapshot,
            artifact_class,
        )

    def get(
        self, principal: SessionPrincipal, job_id: JobId
    ) -> ResearchJobView | None:
        return self._jobs.get_job(principal.user_id, job_id)


class PersistentResearchWorkerControl:
    """Claim and renew work without receiving browser or membership facts."""

    __slots__ = ("_claims", "_heartbeats", "_finalization")

    def __init__(
        self, claims: ResearchJobClaim, heartbeats: ResearchJobHeartbeat,
        finalization: ResearchJobFinalization | None = None,
    ) -> None:
        self._claims = claims
        self._heartbeats = heartbeats
        self._finalization = finalization

    def __repr__(self) -> str:
        return "PersistentResearchWorkerControl()"

    def claim(self, worker_id: ResearchWorkerId) -> ClaimedResearchJob | None:
        return self._claims.claim_next(worker_id)

    def heartbeat(
        self,
        job_id: JobId,
        expected_revision: ResearchJobRevisionId,
        worker_id: ResearchWorkerId,
        claim_id: ResearchJobClaimId,
    ) -> RenewedResearchJobLease | None:
        return self._heartbeats.heartbeat(
            job_id, expected_revision, worker_id, claim_id
        )

    def finalize_success(self, claimed: ClaimedResearchJob, summary, artifact) -> CompletedResearchJob | None:
        if self._finalization is None:
            raise RuntimeError("research job finalization is not configured")
        return self._finalization.finalize_success(
            claimed.job_id, claimed.revision_id, claimed.worker_id,
            claimed.claim_id, summary, artifact,
        )

    def finalize_failure(self, claimed: ClaimedResearchJob,
                         code: ResearchJobFailureCode) -> CompletedResearchJob | None:
        if self._finalization is None:
            raise RuntimeError("research job finalization is not configured")
        return self._finalization.finalize_failure(
            claimed.job_id, claimed.revision_id, claimed.worker_id,
            claimed.claim_id, code,
        )
