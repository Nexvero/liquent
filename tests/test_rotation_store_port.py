from datetime import UTC, datetime, timedelta

import pytest

from liquent_platform.identity.ports import BrowserSessionRotationStore
from liquent_platform.identity.session import (
    IssuedBrowserSession,
    SessionId,
)


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)
CURRENT_ID = SessionId("current-session")
REPLACEMENT_ID = SessionId("replacement-session")


class StubRotationStore:
    def __init__(self, *, rotated: bool = True) -> None:
        self.rotated = rotated
        self.calls: list[tuple[SessionId, IssuedBrowserSession]] = []

    def rotate_session(
        self,
        current_id: SessionId,
        replacement: IssuedBrowserSession,
    ) -> bool:
        self.calls.append((current_id, replacement))
        return self.rotated


def _replacement() -> IssuedBrowserSession:
    return IssuedBrowserSession(
        REPLACEMENT_ID,
        "replacement-csrf-proof",
        NOW + timedelta(minutes=1),
    )


def _rotate(port: BrowserSessionRotationStore) -> bool:
    return port.rotate_session(CURRENT_ID, _replacement())


def test_rotation_store_port_accepts_atomic_rotate_contract() -> None:
    store = StubRotationStore()

    assert _rotate(store) is True
    assert len(store.calls) == 1
    current_id, replacement = store.calls[0]
    assert current_id == CURRENT_ID
    assert replacement.session_id == REPLACEMENT_ID
    assert replacement.csrf_token == "replacement-csrf-proof"


def test_rotation_store_receives_only_issued_material_no_principal() -> None:
    # The port carries current id and issued replacement material only; there is
    # no principal argument, so a caller cannot bind a foreign principal.
    store = StubRotationStore()

    _rotate(store)

    _current_id, replacement = store.calls[0]
    assert isinstance(replacement, IssuedBrowserSession)
    assert not hasattr(replacement, "principal")


@pytest.mark.parametrize("reason", ["invalid_source", "target_collision"])
def test_rotation_store_reports_neutral_false(reason: str) -> None:
    store = StubRotationStore(rotated=False)

    assert _rotate(store) is False
    assert len(store.calls) == 1


def test_rotation_outcome_is_a_plain_boolean_without_material() -> None:
    store = StubRotationStore()

    outcome = _rotate(store)

    assert outcome is True
    assert isinstance(outcome, bool)
    assert "replacement-csrf-proof" not in repr(outcome)
    assert "replacement-session" not in repr(outcome)
