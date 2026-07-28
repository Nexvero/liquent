"""Issue new browser-session material and persist its server-side record."""

from datetime import datetime, timedelta

from liquent_platform.application.create_session import create_browser_session
from liquent_platform.identity.ports import (
    BrowserSessionCreationStore,
    BrowserSessionMaterialGenerator,
)
from liquent_platform.identity.session import (
    IssuedBrowserSession,
    SessionPrincipal,
)


def issue_browser_session(
    store: BrowserSessionCreationStore,
    generator: BrowserSessionMaterialGenerator,
    principal: SessionPrincipal,
    *,
    now: datetime,
    lifetime: timedelta,
) -> IssuedBrowserSession:
    """Generate and create one browser session with a fixed positive lifetime."""

    if lifetime <= timedelta(0):
        raise ValueError("session lifetime must be positive")
    issued = IssuedBrowserSession(
        generator.new_session_id(),
        generator.new_csrf_token(),
        now + lifetime,
    )
    return create_browser_session(store, principal, issued)
