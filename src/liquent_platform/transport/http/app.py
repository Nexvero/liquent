"""Minimal HTTP control-plane application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from liquent_platform import __version__
from liquent_platform.application.health import ProcessHealth
from liquent_platform.identity.research import ExperimentId, JobId
from liquent_platform.jobs.in_memory import InMemoryResearchJobs
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


def create_app(
    settings: PlatformSettings | None = None,
    health: ProcessHealth | None = None,
    metrics: ControlPlaneMetrics | None = None,
    research_jobs: InMemoryResearchJobs | None = None,
) -> FastAPI:
    """Create an isolated app after configuration has validated successfully."""

    runtime_settings = settings or PlatformSettings()
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
    def research_job_status(job_id: JobId) -> ResearchJobResponse:
        try:
            job = job_store.get(job_id)
        except KeyError:
            raise HTTPException(404, "research_job_not_found") from None
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

    @app.get(
        "/v1/research/jobs/{job_id}/evidence",
        tags=["research"],
    )
    def research_job_evidence(job_id: JobId):
        try:
            evidence = job_store.get(job_id).evidence
        except KeyError:
            raise HTTPException(404, "research_job_not_found") from None
        if evidence is None:
            raise HTTPException(404, "research_evidence_not_found")
        return evidence

    return app
