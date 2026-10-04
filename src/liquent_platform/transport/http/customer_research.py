"""Bounded customer actions using existing browser sessions and Research queue."""
import base64
import binascii
import hashlib
import json
import secrets

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from liquent.research_pilot.customer_data_check import check_customer_data
from liquent.research_pilot.execution import fingerprint, validate_configuration
from liquent_platform.application.authenticate_session import AuthenticationRequired, require_browser_session
from liquent_platform.application.authorize_research import require_research_authorization
from liquent_platform.application.authorization_errors import ResearchAuthorizationDenied
from liquent_platform.application.csrf import CsrfValidationFailed, require_valid_csrf_token
from liquent_platform.application.resolve_workspace_research_read import resolve_workspace_research_read
from liquent_platform.identity.access import Permission
from liquent_platform.identity.session import SessionId
from liquent_platform.identity.research import ResearchJobAcceptanceId
from liquent_platform.identity.research_job import ResearchJobAcceptanceConflict, ResearchResultArtifactClass
from liquent_platform.persistence.identity_errors import BrowserSessionStoreUnavailable, WorkspaceMembershipStoreUnavailable, ResearchJobStoreUnavailable
from liquent_platform.persistence.customer_research import CustomerResearchUnavailable

from .research_customer_ui import CUSTOMER_SCRIPT

LIMIT = 5 * 1024 * 1024


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


async def _body(request: Request, fields: set[str], limit: int = 7 * 1024 * 1024) -> dict:
    if request.query_params or request.headers.get("content-type", "").split(";")[0] != "application/json":
        raise HTTPException(400, "invalid_request")
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > limit:
            raise HTTPException(413, "request_too_large")
        raw.extend(chunk)
    try:
        value = json.loads(raw, object_pairs_hook=_object, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if type(value) is not dict or set(value) != fields:
            raise ValueError()
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise HTTPException(422, "invalid_request") from None


def _csv(value) -> bytes:
    if type(value) is not str or len(value) > ((LIMIT + 2) // 3) * 4:
        raise HTTPException(413, "dataset_too_large")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, "invalid_dataset_encoding") from None
    if not raw or len(raw) > LIMIT:
        raise HTTPException(413, "dataset_too_large")
    return raw


def register_customer_research(app, *, sessions, memberships, contexts, store, control):
    def authorize(request: Request, *, write=False, mutation=True):
        try:
            session = require_browser_session(sessions, SessionId(request.cookies.get("liquent_session", "")))
            context = resolve_workspace_research_read(contexts, memberships, session.principal)
            if context is None:
                raise HTTPException(403, "permission_denied")
            if mutation:
                require_valid_csrf_token(session.expected_csrf_token, request.headers.get("X-CSRF-Token"))
            if write:
                require_research_authorization(memberships, session.principal, context.workspace_id, Permission.RESEARCH_WRITE)
            return session, context
        except (AuthenticationRequired, ValueError):
            raise HTTPException(401, "authentication_required") from None
        except (CsrfValidationFailed, ResearchAuthorizationDenied):
            raise HTTPException(403, "permission_denied") from None
        except (BrowserSessionStoreUnavailable, WorkspaceMembershipStoreUnavailable):
            raise HTTPException(503, "research_unavailable") from None

    def response(value, code=200):
        return JSONResponse(value, status_code=code, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"})

    @app.get("/research/customer.js", include_in_schema=False)
    def customer_script():
        return Response(CUSTOMER_SCRIPT, media_type="text/javascript", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    @app.get("/v1/research/customer-context", include_in_schema=False)
    def context(request: Request):
        if request.query_params:
            raise HTTPException(400, "invalid_request")
        session, workspace = authorize(request, mutation=False)
        can_write = False
        try:
            require_research_authorization(memberships, session.principal, workspace.workspace_id, Permission.RESEARCH_WRITE)
            can_write = control is not None and store is not None
        except ResearchAuthorizationDenied:
            pass
        return response({"csrf_token": session.expected_csrf_token, "can_write": can_write})

    @app.post("/v1/research/data-check", include_in_schema=False)
    async def data_check(request: Request):
        authorize(request)
        value = await _body(request, {"csv_base64", "timeframe"})
        try:
            result = await run_in_threadpool(check_customer_data, _csv(value["csv_base64"]), value["timeframe"])
        except ValueError:
            raise HTTPException(422, "invalid_data_check") from None
        return response(result)

    async def preview_inputs(request, fields):
        value = await _body(request, fields)
        raw = _csv(value["csv_base64"])
        try:
            if len(json.dumps(value["configuration"], ensure_ascii=False).encode("utf-8")) > 65536:
                raise ValueError()
            config = validate_configuration(value["configuration"])
            quality = await run_in_threadpool(check_customer_data, raw, config["dataset"]["timeframe"])
            if quality["status"] == "blocked":
                raise ValueError()
            binding = fingerprint({"dataset_fingerprint": "sha256:" + hashlib.sha256(raw).hexdigest(), "configuration": config})
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise HTTPException(422, "research_inputs_invalid") from None
        return value, raw, config, binding

    @app.post("/v1/research/request-preview", include_in_schema=False)
    async def preview(request: Request):
        authorize(request)
        _, _, config, binding = await preview_inputs(request, {"csv_base64", "configuration"})
        return response({"binding_fingerprint": binding, "variant_ids": [variant["id"] for variant in config["variants"]], "order_created": False, "simulation_started": False})

    @app.post("/v1/research/customer-jobs", include_in_schema=False)
    async def submit(request: Request):
        session, workspace = authorize(request, write=True)
        if store is None or control is None:
            raise HTTPException(503, "research_unavailable")
        value, raw, config, _ = await preview_inputs(request, {"csv_base64", "configuration", "binding_fingerprint", "data_rights", "execution_approved"})
        try:
            snapshot = await run_in_threadpool(store.bind_request, str(session.principal.user_id), str(workspace.workspace_id), raw, config,
                                              value["binding_fingerprint"], value["data_rights"], value["execution_approved"])
            accepted = await run_in_threadpool(control.accept, session, request.headers.get("X-CSRF-Token"),
                                              ResearchJobAcceptanceId(hashlib.sha256(str(snapshot.experiment_id).encode()).hexdigest()), snapshot, ResearchResultArtifactClass.BACKTEST_RESULT_V1)
            if accepted is None:
                raise HTTPException(403, "permission_denied")
            if isinstance(accepted, ResearchJobAcceptanceConflict):
                raise HTTPException(409, "research_conflict")
            current = await run_in_threadpool(control.get, session.principal, accepted.job_id)
            if current is None:
                raise HTTPException(403, "permission_denied")
        except ValueError:
            raise HTTPException(422, "research_approval_or_binding_invalid") from None
        except (CsrfValidationFailed, ResearchAuthorizationDenied):
            raise HTTPException(403, "permission_denied") from None
        except (ResearchJobStoreUnavailable, CustomerResearchUnavailable):
            raise HTTPException(503, "research_unavailable") from None
        return response({"job_id": str(accepted.job_id), "status": current.status.value}, 202)

    @app.post("/v1/research/customer-feedback", include_in_schema=False)
    async def feedback(request: Request):
        session, workspace = authorize(request)
        if store is None:
            raise HTTPException(503, "feedback_unavailable")
        value = await _body(request, {"feedback", "synthetic"}, 16384)
        try:
            await run_in_threadpool(store.save_feedback, str(session.principal.user_id), str(workspace.workspace_id), value["feedback"], value["synthetic"])
        except ValueError:
            raise HTTPException(422, "invalid_feedback") from None
        except (ResearchJobStoreUnavailable, CustomerResearchUnavailable):
            raise HTTPException(503, "feedback_unavailable") from None
        return response({"saved": True, "order_created": False, "execution_approved": False, "evidence_type": "self_report_not_purchase"})
