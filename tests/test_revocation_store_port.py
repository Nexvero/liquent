from liquent_platform.identity.ports import BrowserSessionRevocationStore
from liquent_platform.identity.session import SessionId


KNOWN_ID = SessionId("known-session")
UNKNOWN_ID = SessionId("unknown-session")


class StubRevocationStore:
    """Records revocations and always returns None, whatever the id's state."""

    def __init__(self, known: set[SessionId] | None = None) -> None:
        self.known = known or set()
        self.calls: list[SessionId] = []

    def revoke_session(self, session_id: SessionId) -> None:
        self.calls.append(session_id)
        return None


def _revoke(port: BrowserSessionRevocationStore, session_id: SessionId) -> None:
    return port.revoke_session(session_id)


def test_revocation_store_port_accepts_revoke_contract() -> None:
    store = StubRevocationStore()

    assert _revoke(store, KNOWN_ID) is None
    assert store.calls == [KNOWN_ID]


def test_known_and_unknown_ids_return_the_same_none() -> None:
    store = StubRevocationStore(known={KNOWN_ID})

    assert _revoke(store, KNOWN_ID) is None
    assert _revoke(store, UNKNOWN_ID) is None


def test_repeated_revocation_stays_neutral() -> None:
    store = StubRevocationStore(known={KNOWN_ID})

    assert _revoke(store, KNOWN_ID) is None
    assert _revoke(store, KNOWN_ID) is None
    assert store.calls == [KNOWN_ID, KNOWN_ID]


def test_revocation_result_carries_no_session_data() -> None:
    store = StubRevocationStore(known={KNOWN_ID})

    outcome = _revoke(store, KNOWN_ID)

    assert outcome is None
    assert "known-session" not in repr(outcome)
