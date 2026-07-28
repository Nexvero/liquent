"""Create one server-side browser session without storage assumptions."""

from liquent_platform.application.session_lifecycle_errors import (
    SessionLifecycleConflict,
)
from liquent_platform.identity.ports import BrowserSessionCreationStore
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    IssuedBrowserSession,
    ResolvedBrowserSession,
    SessionPrincipal,
)


def create_browser_session(
    store: BrowserSessionCreationStore,
    principal: SessionPrincipal,
    issued: IssuedBrowserSession,
) -> IssuedBrowserSession:
    """Persist one new session atomically or report a neutral conflict."""

    record = BrowserSessionRecord(
        ResolvedBrowserSession(principal, issued.csrf_token),
        issued.expires_at,
    )
    if not store.add_session(issued.session_id, record):
        raise SessionLifecycleConflict
    return issued
