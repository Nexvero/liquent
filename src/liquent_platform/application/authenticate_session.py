"""Resolve one browser session without exposing authentication details."""

from liquent_platform.identity.ports import BrowserSessionLookup
from liquent_platform.identity.session import ResolvedBrowserSession, SessionId


class AuthenticationRequired(Exception):
    """Report every missing or invalid browser session identically."""

    code = "authentication_required"

    def __init__(self) -> None:
        super().__init__(self.code)


def require_browser_session(
    sessions: BrowserSessionLookup,
    session_id: SessionId | None,
) -> ResolvedBrowserSession:
    """Return one resolved session or raise the neutral authentication error."""

    if session_id is None:
        raise AuthenticationRequired
    session = sessions.get_session(session_id)
    if session is None:
        raise AuthenticationRequired
    return session

