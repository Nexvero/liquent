"""Minimal HTTP control-plane application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Annotated, AsyncIterator, Callable

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
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
from liquent_platform.application.csrf import (
    CsrfValidationFailed,
    require_valid_csrf_token,
)
from liquent_platform.application.oidc_login_errors import (
    OidcLoginStartConflict,
    OidcLoginUnavailable,
)
from liquent_platform.application.prepare_oidc_login_authorization import (
    prepare_oidc_login_authorization,
)
from liquent_platform.application.read_research_job import get_authorized_research_job
from liquent_platform.application.revoke_session import revoke_browser_session
from liquent_platform.application.session_lifecycle_errors import (
    SessionRevocationUnavailable,
)
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
from liquent_platform.identity.oidc_login_material import (
    SecureOidcLoginMaterialGenerator,
)
from liquent_platform.identity.ports import (
    ActiveOidcClientConfigurationLookup,
    BrowserSessionLookup,
    BrowserSessionRevocationStore,
    OidcLoginTransactionCreationStore,
    WorkspaceMembershipLookup,
)
from liquent_platform.identity.session import ResolvedBrowserSession, SessionId
from liquent_platform.transport.http.oidc_state_cookie import set_oidc_state_cookie
from liquent_platform.transport.http.session_cookie import clear_session_cookie
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
    logout_sessions: BrowserSessionLookup | None = None,
    logout_revocations: BrowserSessionRevocationStore | None = None,
    oidc_login_configurations: ActiveOidcClientConfigurationLookup | None = None,
    oidc_login_transactions: OidcLoginTransactionCreationStore | None = None,
    oidc_login_material: SecureOidcLoginMaterialGenerator | None = None,
    oidc_login_clock: Callable[[], datetime] | None = None,
    oidc_login_lifetime: timedelta | None = None,
    oidc_login_origin: str | None = None,
) -> FastAPI:
    """Create an isolated app after configuration has validated successfully."""

    runtime_settings = settings or PlatformSettings()
    if (research_sessions is None) is not (research_memberships is None):
        raise ValueError(
            "research session lookup and membership lookup must be provided together"
        )
    if (logout_sessions is None) is not (logout_revocations is None):
        raise ValueError(
            "logout session lookup and revocation store must be provided together"
        )
    # The login-start route is unauthenticated and creates server-side state, so
    # it exists only when every dependency it needs was injected explicitly. A
    # partial combination is a configuration error, never a route that silently
    # falls back to a system clock or a guessed trusted origin.
    oidc_login_dependencies = (
        oidc_login_configurations,
        oidc_login_transactions,
        oidc_login_material,
        oidc_login_clock,
        oidc_login_lifetime,
        oidc_login_origin,
    )
    oidc_login_enabled = all(
        dependency is not None for dependency in oidc_login_dependencies
    )
    if not oidc_login_enabled and any(
        dependency is not None for dependency in oidc_login_dependencies
    ):
        raise ValueError(
            "oidc login start requires configuration lookup, transaction store, "
            "material generator, clock, lifetime, and trusted origin together"
        )
    if oidc_login_enabled:
        if oidc_login_lifetime <= timedelta(0):
            raise ValueError("oidc login transaction lifetime must be positive")
        # Exactly one origin: a separator would smuggle a list into a value that
        # must be compared for exact equality against the Origin header.
        if not oidc_login_origin or any(
            character.isspace() or character == ","
            for character in oidc_login_origin
        ):
            raise ValueError(
                "trusted oidc login origin must be exactly one non-empty origin"
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

    if logout_sessions is not None and logout_revocations is not None:

        def _neutral_cleared() -> Response:
            cleared = Response(status_code=status.HTTP_204_NO_CONTENT)
            clear_session_cookie(cleared)  # deletes cookie + Cache-Control: no-store
            return cleared

        def _no_store(status_code: int) -> Response:
            result = Response(status_code=status_code)
            result.headers["Cache-Control"] = "no-store"
            return result

        @app.post("/v1/session/logout", tags=["session"])
        def logout(
            session_cookie: Annotated[
                str | None,
                Cookie(alias="liquent_session"),
            ] = None,
            csrf_token: Annotated[
                str | None,
                Header(alias="X-CSRF-Token"),
            ] = None,
        ) -> Response:
            # Missing cookie: no lookup, no revocation, neutral cleared 204.
            if session_cookie is None:
                return _neutral_cleared()
            # Unknown, expired, or revoked all resolve to None: neutral cleared 204.
            session = logout_sessions.get_session(SessionId(session_cookie))
            if session is None:
                return _neutral_cleared()
            # Valid active session: the bound CSRF proof is mandatory.
            try:
                require_valid_csrf_token(session.expected_csrf_token, csrf_token)
            except CsrfValidationFailed:
                return _no_store(status.HTTP_403_FORBIDDEN)  # no revoke, keep cookie
            # CSRF valid: revoke exactly once, then clear the cookie.
            try:
                revoke_browser_session(logout_revocations, SessionId(session_cookie))
            except SessionRevocationUnavailable:
                return _no_store(status.HTTP_500_INTERNAL_SERVER_ERROR)  # keep cookie
            return _neutral_cleared()

    if oidc_login_enabled:

        def _rejected(status_code: int) -> Response:
            """One neutral empty rejection: no cookie, no redirect, no detail."""

            rejected = Response(status_code=status_code)
            rejected.headers["Cache-Control"] = "no-store"
            return rejected

        # Every method on this path is owned deliberately. Registering POST alone
        # would let Starlette raise HTTPException(405), which FastAPI renders as a
        # JSON body — that contradicts the empty-body contract. Owning the path
        # keeps the answer empty without installing a global exception handler
        # that would change unrelated routes.
        @app.api_route(
            "/v1/session/oidc/login",
            methods=["POST", "GET", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS"],
            tags=["session"],
        )
        async def start_oidc_login_route(request: Request) -> Response:
            if request.method != "POST":
                # A login start creates server-side state and is never a safe
                # method; prefetching or a link scanner must not open one.
                not_allowed = _rejected(status.HTTP_405_METHOD_NOT_ALLOWED)
                not_allowed.headers["Allow"] = "POST"
                return not_allowed
            # The route takes no browser-supplied business value at all: no
            # issuer, provider, client id, redirect uri, scope, admission id, or
            # return path. Anything sent is a contract violation, not an input.
            if request.url.query:
                return _rejected(status.HTTP_400_BAD_REQUEST)
            if await request.body():
                return _rejected(status.HTTP_400_BAD_REQUEST)
            # Unauthenticated, so no Liquent CSRF token exists yet. The trusted
            # origin is injected and never derived from Host, Forwarded,
            # X-Forwarded-Host, query, or body; Referer is no substitute. A
            # missing header and the opaque "null" both fail this comparison.
            if request.headers.get("origin") != oidc_login_origin:
                return _rejected(status.HTTP_403_FORBIDDEN)
            fetch_site = request.headers.get("sec-fetch-site")
            if fetch_site is not None and fetch_site != "same-origin":
                # cross-site, same-site, none, and any unknown value are refused.
                return _rejected(status.HTTP_403_FORBIDDEN)
            # Only now is the clock read, exactly once, and the same value bounds
            # both the stored transaction and the binding cookie.
            now = oidc_login_clock()
            try:
                prepared = prepare_oidc_login_authorization(
                    oidc_login_configurations,
                    oidc_login_transactions,
                    oidc_login_material,
                    now=now,
                    lifetime=oidc_login_lifetime,
                    admission_id=None,
                    return_path=None,
                )
            except (OidcLoginUnavailable, OidcLoginStartConflict):
                # Unified on purpose: telling the two apart would reveal whether
                # an active configuration exists or whether a state collided.
                # No Retry-After — there is no defensible retry time to state.
                return _rejected(status.HTTP_503_SERVICE_UNAVAILABLE)
            except Exception:
                # Route-local and neutral: no exception text, no internal detail.
                return _rejected(status.HTTP_500_INTERNAL_SERVER_ERROR)
            # Reached only after the transaction was stored atomically. A failure
            # from here on still answers neutrally and empty; the store is never
            # rolled back, because a rollback would itself be a reuse path. The
            # orphaned pending record expires fail-closed and is never reused.
            try:
                started = Response(status_code=status.HTTP_303_SEE_OTHER)
                # 303 makes the browser follow with GET; a method-preserving
                # 307/308 would repeat the POST at the identity provider. The URL
                # travels in Location only and must stay out of logs.
                started.headers["Location"] = prepared.request.url
                started.headers["Cache-Control"] = "no-store"
                started.headers["Pragma"] = "no-cache"
                # Without this the identity provider would see the previous
                # Liquent URL in Referer.
                started.headers["Referrer-Policy"] = "no-referrer"
                # Straight from the use-case result, never parsed back out of the
                # authorization URL.
                set_oidc_state_cookie(
                    started,
                    prepared.state.value,
                    now=now,
                    lifetime=oidc_login_lifetime,
                )
            except Exception:
                return _rejected(status.HTTP_500_INTERNAL_SERVER_ERROR)
            return started

    return app
