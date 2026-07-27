from liquent_platform.identity.access import UserId
from liquent_platform.identity.ports import BrowserSessionLookup
from liquent_platform.identity.session import (
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)


class StubBrowserSessionLookup:
    def __init__(self, session: ResolvedBrowserSession | None) -> None:
        self.session = session
        self.requested: SessionId | None = None

    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None:
        self.requested = session_id
        return self.session


def _lookup(
    port: BrowserSessionLookup,
    session_id: SessionId,
) -> ResolvedBrowserSession | None:
    return port.get_session(session_id)


def test_browser_session_lookup_uses_opaque_session_identity() -> None:
    session = ResolvedBrowserSession(
        SessionPrincipal(UserId("user-1")),
        "session-proof",
    )
    lookup = StubBrowserSessionLookup(session)

    assert _lookup(lookup, SessionId("opaque-session")) is session
    assert lookup.requested == SessionId("opaque-session")


def test_missing_browser_session_is_neutral_none() -> None:
    lookup = StubBrowserSessionLookup(None)

    assert _lookup(lookup, SessionId("unknown-session")) is None

