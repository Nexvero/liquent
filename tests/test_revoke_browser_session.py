import inspect

from liquent_platform.application.revoke_session import revoke_browser_session
from liquent_platform.identity.session import SessionId


SESSION_ID = SessionId("opaque-session")
OTHER_ID = SessionId("other-session")


class StubRevocationStore:
    def __init__(self) -> None:
        self.calls: list[SessionId] = []

    def revoke_session(self, session_id: SessionId) -> None:
        self.calls.append(session_id)
        return None


def test_revoke_delegates_exactly_once_to_store() -> None:
    store = StubRevocationStore()

    result = revoke_browser_session(store, SESSION_ID)

    assert result is None
    assert store.calls == [SESSION_ID]


def test_revoke_is_neutral_for_known_and_unknown_ids() -> None:
    store = StubRevocationStore()

    assert revoke_browser_session(store, SESSION_ID) is None
    assert revoke_browser_session(store, OTHER_ID) is None
    assert store.calls == [SESSION_ID, OTHER_ID]


def test_repeated_revocation_through_use_case_stays_neutral() -> None:
    store = StubRevocationStore()

    revoke_browser_session(store, SESSION_ID)
    revoke_browser_session(store, SESSION_ID)

    assert store.calls == [SESSION_ID, SESSION_ID]


def test_revoke_result_has_no_session_data() -> None:
    store = StubRevocationStore()

    outcome = revoke_browser_session(store, SESSION_ID)

    assert outcome is None
    assert "opaque-session" not in repr(outcome)


def test_revoke_use_case_takes_only_store_and_session_id() -> None:
    parameters = list(inspect.signature(revoke_browser_session).parameters)

    assert parameters == ["store", "session_id"]


def test_revoke_has_no_side_effects_beyond_single_delegation() -> None:
    # The store exposes only revoke_session; the use case must not touch anything
    # else and must call it exactly once.
    store = StubRevocationStore()

    revoke_browser_session(store, SESSION_ID)

    assert len(store.calls) == 1
