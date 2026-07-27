import pytest

from liquent_platform.application.authenticate_session import (
    AuthenticationRequired,
    require_browser_session,
)
from liquent_platform.identity.access import UserId
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


def _session() -> ResolvedBrowserSession:
    return ResolvedBrowserSession(
        SessionPrincipal(UserId("user-1")),
        "session-proof",
    )


def test_existing_browser_session_is_returned() -> None:
    session = _session()
    sessions = StubBrowserSessionLookup(session)

    assert require_browser_session(sessions, SessionId("opaque-session")) is session
    assert sessions.requested == SessionId("opaque-session")


def test_missing_session_id_fails_without_lookup() -> None:
    sessions = StubBrowserSessionLookup(_session())

    with pytest.raises(AuthenticationRequired) as captured:
        require_browser_session(sessions, None)

    assert captured.value.code == "authentication_required"
    assert str(captured.value) == "authentication_required"
    assert sessions.requested is None


def test_unknown_session_uses_same_neutral_error() -> None:
    sessions = StubBrowserSessionLookup(None)

    with pytest.raises(AuthenticationRequired) as captured:
        require_browser_session(sessions, SessionId("unknown-session"))

    assert str(captured.value) == "authentication_required"
    assert captured.value.args == ("authentication_required",)
    assert sessions.requested == SessionId("unknown-session")

