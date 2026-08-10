"""Minimal HTTP control-plane application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from hmac import compare_digest
from typing import Annotated, AsyncIterator, Callable
from urllib.parse import urlsplit

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
from liquent_platform.application.complete_oidc_login import complete_oidc_login
from liquent_platform.application.csrf import (
    CsrfValidationFailed,
    require_valid_csrf_token,
)
from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
    resolve_internal_destination,
)
from liquent_platform.application.oidc_login_errors import (
    OidcLoginStartConflict,
    OidcLoginUnavailable,
)
from liquent_platform.application.verify_oidc_callback import verify_oidc_callback
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
from liquent_platform.identity.oidc_login_transaction import OidcLoginState
from liquent_platform.identity.ports import (
    ActiveOidcClientConfigurationLookup,
    BrowserSessionCreationStore,
    BrowserSessionLookup,
    BrowserSessionMaterialGenerator,
    BrowserSessionRevocationStore,
    ExternalIdentityAdmissionStore,
    ExternalIdentityLookup,
    OidcAuthorizationCodeVerifier,
    OidcLoginTransactionClaimStore,
    OidcLoginTransactionCreationStore,
    WorkspaceMembershipLookup,
)
from liquent_platform.identity.session import ResolvedBrowserSession, SessionId
from liquent_platform.transport.http.oidc_state_cookie import (
    OIDC_STATE_COOKIE_NAME,
    clear_oidc_state_cookie,
    set_oidc_state_cookie,
)
from liquent_platform.transport.http.session_cookie import (
    clear_session_cookie,
    set_issued_session,
)
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


# LQ-175 §4. Enforced on the raw ASGI bytes so the request target stays bounded
# independently of proxy defaults, and so nothing is decoded under an unbounded
# input. Four parameters is exactly the largest permitted provider-error form.
_MAX_RAW_CALLBACK_QUERY_BYTES = 8192
_MAX_RAW_CALLBACK_QUERY_COMPONENTS = 4
_MAX_RAW_CALLBACK_COMPONENT_BYTES = 4096

_CALLBACK_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
    "TRACE",
    "CONNECT",
]


def _raw_callback_query_is_bounded(raw: bytes) -> bool:
    """Bound the untouched query bytes before anything is decoded or read."""

    if len(raw) > _MAX_RAW_CALLBACK_QUERY_BYTES:
        return False
    # Raw "&" split: empty components stay visible and count, and no
    # percent-decoding happens on the way to this decision.
    components = raw.split(b"&")
    if len(components) > _MAX_RAW_CALLBACK_QUERY_COMPONENTS:
        return False
    return all(
        len(component) <= _MAX_RAW_CALLBACK_COMPONENT_BYTES for component in components
    )


def _single_callback_state(parameters: list[tuple[str, str]]) -> str | None:
    """Read exactly one non-empty state from the real multimap, or refuse."""

    values = [value for name, value in parameters if name == "state"]
    if len(values) != 1 or not values[0]:
        return None
    return values[0]


def _callback_authorization_code(parameters: list[tuple[str, str]]) -> str | None:
    """The code of a valid success form; ``None`` for every other form.

    The success form is exactly one state and one non-empty code, so an unknown
    parameter, a duplicate, or an empty code all fail this test. ``None``
    deliberately does not distinguish a valid provider-error form from a
    malformed one: both are neutral business rejections that must still leave
    the transaction consumed fail-closed (LQ-158 §6), which is exactly what the
    verification use case does when it receives ``None``.
    """

    names = [name for name, _ in parameters]
    if len(names) != 2 or set(names) != {"state", "code"}:
        return None
    code = next(value for name, value in parameters if name == "code")
    return code or None


def _require_trusted_https_origin(value: str) -> None:
    """Validate the one trusted origin without ever rewriting it.

    An ``Origin`` header is a scheme, host, and optional port and nothing else,
    and the later comparison is exact. A configured value carrying a path, a
    query, a fragment, or userinfo could therefore never match any browser and
    would fail closed silently, so it is rejected while the app is built instead
    of surfacing later as "login is broken".

    The value is only inspected: nothing is normalized, canonicalized, defaulted,
    or returned, so the exact configured string stays what the handler compares
    against. Messages name the setting but never echo the value.

    Three checks run against the raw string on purpose, because the parser hides
    what they look for: it strips tab, newline, and carriage return anywhere in
    the URL, it lowercases the scheme, and it reports an empty query or fragment
    identically to an absent one.
    """

    if not value:
        raise ValueError("trusted oidc login origin must not be empty")
    # Raw value: a separator would smuggle a list into a single-origin setting,
    # and urlsplit would silently clean control characters the handler keeps.
    if any(
        character.isspace()
        or ord(character) < 0x20
        or ord(character) == 0x7F
        or character == ","
        for character in value
    ):
        raise ValueError(
            "trusted oidc login origin must be exactly one origin without "
            "whitespace, control characters, or separators"
        )
    # Raw value: urlsplit lowercases the scheme, so "HTTPS://host" would parse as
    # https while the stored string could never equal a browser's Origin header.
    if not value.startswith("https://"):
        raise ValueError("trusted oidc login origin must be an absolute https origin")
    # Raw value: for "https://host?" and "https://host#" the parsed query and
    # fragment are both empty strings, so a truthiness check would let an empty
    # separator through.
    if "?" in value:
        raise ValueError("trusted oidc login origin must not contain a query")
    if "#" in value:
        raise ValueError("trusted oidc login origin must not contain a fragment")
    parsed = urlsplit(value)
    if not parsed.hostname:
        raise ValueError("trusted oidc login origin must have a host")
    # Checked against None rather than truthiness so an empty userinfo such as
    # "https://@host" is rejected too.
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("trusted oidc login origin must not contain userinfo")
    # An origin has no path at all, not even the bare "/" a browser omits.
    if parsed.path:
        raise ValueError("trusted oidc login origin must not contain a path")
    try:
        port = parsed.port  # the access itself validates the port syntax
    except ValueError:
        # The parser's own message quotes the offending port, so it is replaced
        # by a neutral one. No default port is added and none is normalized.
        raise ValueError("trusted oidc login origin must have a valid port") from None
    # A bare "https://host:" leaves the port empty and port 0 is never a real
    # listener; both would only ever fail the exact header comparison.
    if parsed.netloc.endswith(":") or port == 0:
        raise ValueError("trusted oidc login origin must have a valid port")


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
    oidc_callback_transactions: OidcLoginTransactionClaimStore | None = None,
    oidc_callback_verifier: OidcAuthorizationCodeVerifier | None = None,
    oidc_callback_identities: ExternalIdentityLookup | None = None,
    oidc_callback_admissions: ExternalIdentityAdmissionStore | None = None,
    oidc_callback_sessions: BrowserSessionCreationStore | None = None,
    oidc_callback_material: BrowserSessionMaterialGenerator | None = None,
    oidc_session_lifetime: timedelta | None = None,
    oidc_callback_rejection: ValidatedInternalDestination | None = None,
    oidc_callback_unavailable: ValidatedInternalDestination | None = None,
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
    oidc_login_own = (
        oidc_login_configurations,
        oidc_login_transactions,
        oidc_login_material,
        oidc_login_lifetime,
        oidc_login_origin,
    )
    # The server clock belongs to both routes, so it is listed apart: it must not
    # count as a lonely dependency of the route that does not want it. Either
    # route can be enabled without the other.
    oidc_callback_own = (
        oidc_callback_transactions,
        oidc_callback_verifier,
        oidc_callback_identities,
        oidc_callback_admissions,
        oidc_callback_sessions,
        oidc_callback_material,
        oidc_session_lifetime,
        oidc_callback_rejection,
        oidc_callback_unavailable,
    )
    oidc_login_enabled = oidc_login_clock is not None and all(
        dependency is not None for dependency in oidc_login_own
    )
    oidc_callback_enabled = oidc_login_clock is not None and all(
        dependency is not None for dependency in oidc_callback_own
    )
    login_message = (
        "oidc login start requires configuration lookup, transaction store, "
        "material generator, clock, lifetime, and trusted origin together"
    )
    if not oidc_login_enabled and any(
        dependency is not None for dependency in oidc_login_own
    ):
        raise ValueError(login_message)
    if not oidc_callback_enabled and any(
        dependency is not None for dependency in oidc_callback_own
    ):
        raise ValueError(
            "oidc callback requires claim store, verifier, identity lookup, "
            "admission store, session store, session material generator, clock, "
            "session lifetime, and both validated destinations together"
        )
    if oidc_login_clock is not None and not (oidc_login_enabled or oidc_callback_enabled):
        # A clock on its own enables nothing and is still a configuration error.
        raise ValueError(login_message)
    if oidc_callback_enabled:
        # Same whole-second reasoning as the login start: a sub-second lifetime
        # truncates to Max-Age=0, which a browser treats as already expired, so a
        # successful login would hand out a cookie the browser drops at once.
        if not isinstance(oidc_session_lifetime, timedelta):
            raise ValueError("oidc session lifetime must be a timedelta")
        if int(oidc_session_lifetime.total_seconds()) < 1:
            raise ValueError("oidc session lifetime must be at least one whole second")
    if oidc_login_enabled:
        # Rejected fail-fast on the whole-second Max-Age the cookie would carry,
        # not merely on a positive timedelta: a sub-second lifetime truncates to
        # Max-Age=0, which a browser treats as an immediately expired cookie. A
        # start that cannot bind the browser must never look successful.
        if int(oidc_login_lifetime.total_seconds()) <= 0:
            raise ValueError(
                "oidc login transaction lifetime must be at least one whole second"
            )
        _require_trusted_https_origin(oidc_login_origin)
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
        # that would change unrelated routes. TRACE and CONNECT are listed for the
        # same reason: they are ordinary HTTP methods a client can send at this
        # path, and they must meet the same empty 405 as every other non-POST.
        @app.api_route(
            "/v1/session/oidc/login",
            methods=[
                "POST",
                "GET",
                "HEAD",
                "PUT",
                "PATCH",
                "DELETE",
                "OPTIONS",
                "TRACE",
                "CONNECT",
            ],
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
            # Only now is the clock read, at most once, and the same value bounds
            # both the stored transaction and the binding cookie. A failing clock
            # is an internal fault like any other: it answers neutrally and the
            # use case is never reached, so no transaction is started with a time
            # nobody could vouch for.
            try:
                now = oidc_login_clock()
            except Exception:
                return _rejected(status.HTTP_500_INTERNAL_SERVER_ERROR)
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

    if oidc_callback_enabled:

        def _callback_redirect(destination: ValidatedInternalDestination) -> Response:
            """One empty 303 to an already validated internal target (LQ-175)."""

            redirect = Response(status_code=status.HTTP_303_SEE_OTHER)
            # Only ever the validated value: no raw return path, no origin, no
            # query, and never an absolute URL.
            redirect.headers["Location"] = destination.value
            return redirect

        def _finished(response: Response) -> Response:
            """Close every answer of this route, immediately before returning."""

            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
            response.headers["Referrer-Policy"] = "no-referrer"
            return response

        def _matched_state(request: Request) -> OidcLoginState | None:
            """Bind the browser, or refuse without touching anything.

            Returning a state means the constant-time comparison matched, so the
            binding cookie provably belongs to this transaction. Returning None
            is a neutral pre-match rejection: nothing was claimed and the single
            cookie slot, which may hold a newer login's binding, stays untouched.
            """

            # The untouched ASGI bytes, read before request.query_params exists,
            # so no percent- or unicode-decoding and no framework parameter
            # extraction can happen under an unbounded request target.
            if not _raw_callback_query_is_bounded(request.scope["query_string"]):
                return None
            # The real multimap: a scalar access would hide a duplicate state.
            state = _single_callback_state(request.query_params.multi_items())
            if state is None:
                return None
            # Built before the comparison on purpose: an unusable state value is
            # a technical fault, and nothing may fail after a match has already
            # succeeded, or a matched binding cookie would survive unread.
            validated = OidcLoginState(state)
            bound = request.cookies.get(OIDC_STATE_COOKIE_NAME)
            if bound is None:
                return None
            # Encoded first so a non-ASCII state is an ordinary mismatch rather
            # than a comparison error. The successful comparison is the last
            # operation of this block.
            if not compare_digest(validated.value.encode(), bound.encode()):
                return None
            return validated

        def _handled_after_match(request: Request, state: OidcLoginState) -> Response:
            """Run the four stages once each; the caller clears the cookie."""

            # Exactly one claim, inside the use case, on every path from here:
            # a malformed form yields None and is consumed fail-closed too.
            verified = verify_oidc_callback(
                oidc_callback_transactions,
                oidc_callback_verifier,
                state,
                _callback_authorization_code(request.query_params.multi_items()),
            )
            if verified is None:
                return _callback_redirect(oidc_callback_rejection)
            completed = complete_oidc_login(
                oidc_callback_identities,
                oidc_callback_admissions,
                oidc_callback_sessions,
                oidc_callback_material,
                verified,
                clock=oidc_login_clock,
                lifetime=oidc_session_lifetime,
            )
            if completed is None:
                return _callback_redirect(oidc_callback_rejection)
            destination = resolve_internal_destination(completed.return_path)
            if destination is None:
                # An invalid stored return path never falls back to the default
                # target, and a session already stored server-side stays.
                return _callback_redirect(oidc_callback_rejection)
            # Status and Location first, then the second read of the same
            # injected clock: a rejection above must not touch it, and the
            # cookie's remaining lifetime belongs to this instant. The privacy
            # headers are set by the caller, immediately before returning.
            success = _callback_redirect(destination)
            set_issued_session(success, completed.session, now=oidc_login_clock())
            return success

        @app.api_route(
            "/v1/session/oidc/callback",
            methods=_CALLBACK_METHODS,
            tags=["session"],
        )
        async def oidc_callback_route(request: Request) -> Response:
            if request.method != "GET":
                # Every method on this path is owned deliberately: registering
                # GET alone lets the framework answer OPTIONS, POST, and TRACE
                # with its own JSON body, which the empty-response contract
                # forbids. No dependency, cookie, or Location is involved.
                not_allowed = Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
                not_allowed.headers["Allow"] = "GET"
                return _finished(not_allowed)
            # Pre-match. Nothing on this side may delete the binding cookie, not
            # even a technical fault, so the two exits are kept apart from the
            # post-match block below instead of one blanket handler.
            try:
                state = _matched_state(request)
            except Exception:
                return _finished(_callback_redirect(oidc_callback_unavailable))
            if state is None:
                return _finished(_callback_redirect(oidc_callback_rejection))
            try:
                handled = _handled_after_match(request, state)
            except Exception:
                # The partially built success response stays inside the helper
                # and is dropped unreturned, so neither its session cookie nor
                # its CSRF header can reach this answer. Nothing is rolled back
                # and no stage runs twice.
                handled = _callback_redirect(oidc_callback_unavailable)
            # Post-match, so this runs on every handled exit. delete_cookie
            # appends, exactly like the session cookie's set_cookie, and neither
            # overwrites the other's Set-Cookie header.
            clear_oidc_state_cookie(handled)
            return _finished(handled)

    return app
