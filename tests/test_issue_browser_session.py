from datetime import UTC, datetime, timedelta

import pytest

from liquent_platform.application.issue_session import issue_browser_session
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


class StubMaterialGenerator:
    def __init__(
        self,
        session_id: str = "opaque-session",
        csrf_token: str = "private-csrf-proof",
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


class StubCreationStore:
    def __init__(self, *, added: bool = True) -> None:
        self.added = added
        self.calls: list[tuple[SessionId, BrowserSessionRecord]] = []

    def add_session(
        self,
        session_id: SessionId,
        record: BrowserSessionRecord,
    ) -> bool:
        self.calls.append((session_id, record))
        return self.added


def test_issue_generates_independent_material_and_creates_record() -> None:
    store = StubCreationStore()
    generator = StubMaterialGenerator()
    principal = SessionPrincipal(UserId("user-1"))

    issued = issue_browser_session(
        store,
        generator,
        principal,
        now=NOW,
        lifetime=timedelta(hours=1),
    )

    assert generator.calls == ["session_id", "csrf_token"]
    assert issued.session_id == SessionId("opaque-session")
    assert issued.csrf_token == "private-csrf-proof"
    assert issued.expires_at == NOW + timedelta(hours=1)
    assert len(store.calls) == 1
    session_id, record = store.calls[0]
    assert session_id == issued.session_id
    assert record.session.principal is principal
    assert record.session.expected_csrf_token == issued.csrf_token


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(seconds=-1)])
def test_issue_rejects_non_positive_lifetime_before_side_effects(
    lifetime: timedelta,
) -> None:
    store = StubCreationStore()
    generator = StubMaterialGenerator()

    with pytest.raises(ValueError, match="session lifetime must be positive"):
        issue_browser_session(
            store,
            generator,
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
def test_issue_rejects_empty_generated_material_before_storage(
    session_id: str,
    csrf_token: str,
    message: str,
) -> None:
    store = StubCreationStore()

    with pytest.raises(ValueError, match=message):
        issue_browser_session(
            store,
            StubMaterialGenerator(session_id, csrf_token),
            SessionPrincipal(UserId("user-1")),
            now=NOW,
            lifetime=timedelta(hours=1),
        )

    assert store.calls == []


def test_issue_preserves_neutral_store_conflict() -> None:
    with pytest.raises(SessionLifecycleConflict):
        issue_browser_session(
            StubCreationStore(added=False),
            StubMaterialGenerator(),
            SessionPrincipal(UserId("user-1")),
            now=NOW,
            lifetime=timedelta(hours=1),
        )
