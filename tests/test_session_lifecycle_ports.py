from datetime import UTC, datetime

import pytest

from liquent_platform.application.session_lifecycle_errors import (
    SessionLifecycleConflict,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.ports import BrowserSessionLifecycle
from liquent_platform.identity.session import (
    IssuedBrowserSession,
    SessionId,
    SessionPrincipal,
)


EXPIRES_AT = datetime(2026, 7, 27, 13, tzinfo=UTC)


class StubBrowserSessionLifecycle:
    def __init__(self, issued: IssuedBrowserSession) -> None:
        self.issued = issued
        self.revoked: SessionId | None = None

    def create_session(self, principal: SessionPrincipal) -> IssuedBrowserSession:
        return self.issued

    def rotate_session(
        self, session_id: SessionId
    ) -> IssuedBrowserSession | None:
        return self.issued

    def revoke_session(self, session_id: SessionId) -> None:
        self.revoked = session_id


def _issued() -> IssuedBrowserSession:
    return IssuedBrowserSession(
        SessionId("opaque-session"),
        "private-csrf-proof",
        EXPIRES_AT,
    )


def _use_port(port: BrowserSessionLifecycle) -> None:
    principal = SessionPrincipal(UserId("user-1"))

    assert port.create_session(principal) == _issued()
    assert port.rotate_session(SessionId("old-session")) == _issued()
    port.revoke_session(SessionId("old-session"))


def test_lifecycle_port_supports_three_explicit_commands() -> None:
    lifecycle = StubBrowserSessionLifecycle(_issued())

    _use_port(lifecycle)

    assert lifecycle.revoked == SessionId("old-session")


def test_issued_session_hides_opaque_secrets_from_representation() -> None:
    issued = _issued()

    assert "opaque-session" not in repr(issued)
    assert "private-csrf-proof" not in repr(issued)


@pytest.mark.parametrize(
    ("session_id", "csrf_token", "message"),
    [
        (SessionId(""), "csrf", "session id must not be empty"),
        (SessionId("session"), "", "csrf token must not be empty"),
    ],
)
def test_issued_session_requires_non_empty_secrets(
    session_id: SessionId,
    csrf_token: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        IssuedBrowserSession(session_id, csrf_token, EXPIRES_AT)


def test_issued_session_requires_aware_expiry() -> None:
    with pytest.raises(ValueError, match="expires_at must be timezone-aware"):
        IssuedBrowserSession(
            SessionId("session"),
            "csrf",
            datetime(2026, 7, 27, 13),
        )


def test_lifecycle_conflict_has_one_neutral_public_code() -> None:
    error = SessionLifecycleConflict()

    assert error.code == "session_lifecycle_conflict"
    assert str(error) == "session_lifecycle_conflict"
    assert error.args == ("session_lifecycle_conflict",)


def test_lifecycle_conflict_accepts_no_internal_detail() -> None:
    with pytest.raises(TypeError):
        SessionLifecycleConflict("id collision")  # type: ignore[call-arg]
