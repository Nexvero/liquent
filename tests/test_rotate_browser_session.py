from datetime import UTC, datetime, timedelta

import pytest

from liquent_platform.application.rotate_session import rotate_browser_session
from liquent_platform.application.session_lifecycle_errors import (
    SessionLifecycleConflict,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    SessionId,
    SessionPrincipal,
)


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)
CURRENT_ID = SessionId("current-session")


class StubMaterialGenerator:
    def __init__(
        self,
        session_id: str = "replacement-session",
        csrf_token: str = "replacement-csrf-proof",
    ) -> None:
        self.session_id = session_id
        self.csrf_token = csrf_token
        self.calls: list[str] = []

    def new_session_id(self) -> SessionId:
        self.calls.append("session_id")
        return SessionId(self.session_id)

    def new_csrf_token(self) -> str:
        self.calls.append("csrf_token")
        return self.csrf_token


class StubRotationStore:
    def __init__(self, *, rotated: bool = True) -> None:
        self.rotated = rotated
        self.calls: list[tuple[SessionId, SessionId, BrowserSessionRecord]] = []

    def rotate_session(
        self,
        current_id: SessionId,
        replacement_id: SessionId,
        replacement: BrowserSessionRecord,
    ) -> bool:
        self.calls.append((current_id, replacement_id, replacement))
        return self.rotated


def test_rotate_generates_independent_material_and_keeps_principal() -> None:
    store = StubRotationStore()
    generator = StubMaterialGenerator()
    principal = SessionPrincipal(UserId("user-1"))

    issued = rotate_browser_session(
        store,
        generator,
        CURRENT_ID,
        principal,
        now=NOW,
        lifetime=timedelta(hours=1),
    )

    assert generator.calls == ["session_id", "csrf_token"]
    assert issued.session_id == SessionId("replacement-session")
    assert issued.csrf_token == "replacement-csrf-proof"
    assert issued.expires_at == NOW + timedelta(hours=1)

    assert len(store.calls) == 1
    current_id, replacement_id, replacement = store.calls[0]
    assert current_id == CURRENT_ID
    assert replacement_id == issued.session_id
    assert replacement.session.principal is principal
    assert replacement.session.expected_csrf_token == issued.csrf_token
    assert replacement.expires_at == issued.expires_at
    assert replacement.revoked_at is None


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(seconds=-1)])
def test_rotate_rejects_non_positive_lifetime_before_side_effects(
    lifetime: timedelta,
) -> None:
    store = StubRotationStore()
    generator = StubMaterialGenerator()

    with pytest.raises(ValueError, match="session lifetime must be positive"):
        rotate_browser_session(
            store,
            generator,
            CURRENT_ID,
            SessionPrincipal(UserId("user-1")),
            now=NOW,
            lifetime=lifetime,
        )

    assert generator.calls == []
    assert store.calls == []


@pytest.mark.parametrize(
    ("session_id", "csrf_token", "message"),
    [
        ("", "csrf", "session id must not be empty"),
        ("session", "", "csrf token must not be empty"),
    ],
)
def test_rotate_rejects_empty_generated_material_before_storage(
    session_id: str,
    csrf_token: str,
    message: str,
) -> None:
    store = StubRotationStore()

    with pytest.raises(ValueError, match=message):
        rotate_browser_session(
            store,
            StubMaterialGenerator(session_id, csrf_token),
            CURRENT_ID,
            SessionPrincipal(UserId("user-1")),
            now=NOW,
            lifetime=timedelta(hours=1),
        )

    assert store.calls == []


def test_rotate_reports_store_rejection_as_neutral_conflict() -> None:
    store = StubRotationStore(rotated=False)

    with pytest.raises(SessionLifecycleConflict) as raised:
        rotate_browser_session(
            store,
            StubMaterialGenerator(),
            CURRENT_ID,
            SessionPrincipal(UserId("user-1")),
            now=NOW,
            lifetime=timedelta(hours=1),
        )

    assert str(raised.value) == "session_lifecycle_conflict"
    assert len(store.calls) == 1
