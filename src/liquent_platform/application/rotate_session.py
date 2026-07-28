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
    IssuedBrowserSession,
    SessionId,
)


def rotate_browser_session(
    store: BrowserSessionRotationStore,
    generator: BrowserSessionMaterialGenerator,
    current_id: SessionId,
    *,
    now: datetime,
    lifetime: timedelta,
) -> IssuedBrowserSession:
    """Issue replacement material for one session or report a neutral conflict.

    The replacement principal is not passed in; the atomic store reuses the
    current session's own principal, so this use case cannot bind a foreign one.
    """

    if lifetime <= timedelta(0):
        raise ValueError("session lifetime must be positive")
    replacement = IssuedBrowserSession(
        generator.new_session_id(),
        generator.new_csrf_token(),
        now + lifetime,
    )
    if not store.rotate_session(current_id, replacement):
        raise SessionLifecycleConflict
    return replacement
