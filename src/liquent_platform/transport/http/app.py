"""Minimal HTTP control-plane application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, ConfigDict

from liquent_platform import __version__
from liquent_platform.application.authenticate_session import (
    AuthenticationRequired,
    require_browser_session,
)
from liquent_platform.application.health import ProcessHealth
from liquent_platform.application.evidence import evidence_document
from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.application.authorization_errors import (
    ResearchAuthorizationDenied,
)
from liquent_platform.application.csrf import CsrfValidationFailed
from liquent_platform.application.read_research_job import get_authorized_research_job
from liquent_platform.application.start_research import (
    ResearchRunnerResolver,
    csrf_authorize_resolve_and_start_research_job,
    resolve_and_start_research_job,
)
from liquent_platform.identity.research import (
    ExperimentId,
    JobId,
    StrategyVersionId,
    WorkspaceId,
)
from liquent_platform.identity.ports import (
    BrowserSessionLookup,
    WorkspaceMembershipLookup,
)
from liquent_platform.identity.session import ResolvedBrowserSession, SessionId
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.configuration import PlatformSettings
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.observability.http import ObservabilityMiddleware
from liquent_platform.observability.metrics import ControlPlaneMetrics


class HealthResponse(BaseModel):
    status: str
    service: str = "liquent-control-plane"


class ReadinessResponse(HealthResponse):
    reason: str


class ResearchJobResponse(BaseModel):
    job_id: JobId
    experiment_id: ExperimentId
    status: ResearchJobStatus
    error_code: str | None
    evidence_url: str | None


class ResearchJobStartRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    job_id: JobId
    experiment_id: ExperimentId
    workspace_id: WorkspaceId
    title: str
    dataset_ref: str
    dataset_fingerprint: str
    strategy_version_id: StrategyVersionId
    strategy_parameters: dict[str, str | int | float | bool]
    risk_parameters: dict[str, str | int | float | bool]
    cost_parameters: dict[str, str | int | float | bool]


def create_app(
    settings: PlatformSettings | None = None,
    health: ProcessHealth | None = None,
    metrics: ControlPlaneMetrics | None = None,
    research_jobs: InMemoryResearchJobs | None = None,
    research_resolver: ResearchRunnerResolver | None = None,
    research_sessions: BrowserSessionLookup | None = None,
    research_memberships: WorkspaceMembershipLookup | None = None,
) -> FastAPI:
    """Create an isolated app after configuration has validated successfully."""

    runtime_settings = settings or PlatformSettings()
    if (research_sessions is None) is not (research_memberships is None):
        raise ValueError(
            "research session lookup and membership lookup must be provided together"
        )
    engine = None
    if health is None and runtime_settings.database_url is not None:
        engine = build_engine(runtime_settings.database_url.get_secret_value())
        process_health = ProcessHealth((DatabaseReadinessProbe(engine),))
    else:
        process_health = health or ProcessHealth()
    control_metrics = metrics or ControlPlaneMetrics()
    job_store = research_jobs or InMemoryResearchJobs()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        process_health.mark_started()
        yield
        process_health.mark_stopping()
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="Liquent Control Plane",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    app.state.metrics = control_metrics
    app.state.research_jobs = job_store
    app.add_middleware(ObservabilityMiddleware, metrics=control_metrics)

    def job_response(job: InMemoryResearchJob) -> ResearchJobResponse:
        evidence_url = None
        if job.status is ResearchJobStatus.SUCCEEDED:
            evidence_url = f"/v1/research/jobs/{job.job_id}/evidence"
        return ResearchJobResponse(
            job_id=job.job_id,
            experiment_id=job.snapshot.experiment_id,
            status=job.status,
            error_code=job.error_code,
            evidence_url=evidence_url,
        )

    def current_research_session(
        session_id: Annotated[
            str | None,
            Cookie(alias="liquent_session"),
        ] = None,
    ) -> ResolvedBrowserSession | None:
        if research_sessions is None:
            return None
        try:
            opaque_id = SessionId(session_id) if session_id is not None else None
            return require_browser_session(research_sessions, opaque_id)
        except AuthenticationRequired:
            raise HTTPException(401, "authentication_required") from None

    def visible_job(
        job_id: JobId,
        session: ResolvedBrowserSession | None,
    ) -> InMemoryResearchJob:
        try:
            if session is not None and research_memberships is not None:
                return get_authorized_research_job(
                    job_store,
                    research_memberships,
                    session.principal,
                    job_id,
                )
            return job_store.get(job_id)
        except (KeyError, ResearchAuthorizationDenied):
            raise HTTPException(404, "research_job_not_found") from None

    @app.get("/health/live", response_model=HealthResponse, tags=["operations"])
    def liveness() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/health/ready",
        response_model=ReadinessResponse,
        tags=["operations"],
        responses={503: {"model": ReadinessResponse}},
    )
    def readiness(response: Response) -> ReadinessResponse:
        state = process_health.readiness()
        control_metrics.readiness.set(1 if state.ready else 0)
        if not state.ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="ready" if state.ready else "not_ready",
            reason=state.reason,
        )

    @app.get("/internal/metrics", include_in_schema=False)
    def metrics_endpoint() -> Response:
        return Response(
            content=generate_latest(control_metrics.registry),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.get(
        "/v1/research/jobs/{job_id}",
        response_model=ResearchJobResponse,
        tags=["research"],
    )
    def research_job_status(
        job_id: JobId,
        session: ResolvedBrowserSession | None = Depends(current_research_session),
    ) -> ResearchJobResponse:
        return job_response(visible_job(job_id, session))

    @app.get(
        "/v1/research/jobs/{job_id}/evidence",
        tags=["research"],
    )
    def research_job_evidence(
        job_id: JobId,
        session: ResolvedBrowserSession | None = Depends(current_research_session),
    ):
        evidence = visible_job(job_id, session).evidence
        if evidence is None:
            raise HTTPException(404, "research_evidence_not_found")
        return evidence_document(evidence)

    if research_resolver is not None:

        @app.post(
            "/v1/research/jobs",
            response_model=ResearchJobResponse,
            status_code=status.HTTP_202_ACCEPTED,
            tags=["research"],
        )
        def start_research(
            request: ResearchJobStartRequest,
            session: ResolvedBrowserSession | None = Depends(
                current_research_session
            ),
            csrf_token: Annotated[
                str | None,
                Header(alias="X-CSRF-Token"),
            ] = None,
        ) -> ResearchJobResponse:
            try:
                snapshot = ExperimentSnapshot(
                    experiment_id=request.experiment_id,
                    workspace_id=request.workspace_id,
                    title=request.title,
                    dataset_ref=request.dataset_ref,
                    dataset_fingerprint=request.dataset_fingerprint,
                    strategy_version_id=request.strategy_version_id,
                    strategy_parameters=freeze_parameters(request.strategy_parameters),
                    risk_parameters=freeze_parameters(request.risk_parameters),
                    cost_parameters=freeze_parameters(request.cost_parameters),
                )
                pending_job = InMemoryResearchJob(request.job_id, snapshot)
                if session is not None and research_memberships is not None:
                    job = csrf_authorize_resolve_and_start_research_job(
                        pending_job,
                        research_resolver,
                        job_store,
                        research_memberships,
                        session,
                        csrf_token,
                    )
                else:
                    job = resolve_and_start_research_job(
                        pending_job,
                        research_resolver,
                        job_store,
                    )
            except ResearchAuthorizationDenied:
                raise HTTPException(403, "permission_denied") from None
            except CsrfValidationFailed:
                raise HTTPException(403, "csrf_validation_failed") from None
            except ValueError as exc:
                if str(exc).startswith("research job already exists:"):
                    raise HTTPException(409, "research_job_conflict") from None
                raise HTTPException(422, "research_inputs_unresolvable") from None
            return job_response(job)

    return app
