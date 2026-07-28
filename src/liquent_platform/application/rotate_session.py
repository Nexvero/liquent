"""Rotate one browser session into fresh material without storage assumptions."""

from datetime import datetime, timedelta

from liquent_platform.application.session_lifecycle_errors import (
    SessionLifecycleConflict,
)
from liquent_platform.identity.ports import (
    BrowserSessionMaterialGenerator,
    BrowserSessionRotationStore,
)
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    IssuedBrowserSession,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)


def rotate_browser_session(
    store: BrowserSessionRotationStore,
    generator: BrowserSessionMaterialGenerator,
    current_id: SessionId,
    principal: SessionPrincipal,
    *,
    now: datetime,
    lifetime: timedelta,
) -> IssuedBrowserSession:
    """Issue replacement material for one session or report a neutral conflict."""

    if lifetime <= timedelta(0):
        raise ValueError("session lifetime must be positive")
    issued = IssuedBrowserSession(
        generator.new_session_id(),
        generator.new_csrf_token(),
        now + lifetime,
    )
    replacement = BrowserSessionRecord(
        ResolvedBrowserSession(principal, issued.csrf_token),
        issued.expires_at,
    )
    if not store.rotate_session(current_id, issued.session_id, replacement):
        raise SessionLifecycleConflict
    return issued
