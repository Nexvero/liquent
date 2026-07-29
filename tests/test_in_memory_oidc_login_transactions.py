import inspect
from datetime import UTC, datetime, timedelta

import pytest

import liquent_platform.identity.in_memory as in_memory_mod
from liquent_platform.identity.in_memory import InMemoryOidcLoginTransactions
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.ports import OidcLoginTransactionClaimStore


CREATED = datetime(2026, 7, 29, 12, tzinfo=UTC)
EXPIRES = CREATED + timedelta(minutes=10)
BEFORE_EXPIRY = EXPIRES - timedelta(seconds=1)
AFTER_EXPIRY = EXPIRES + timedelta(seconds=1)

STATE = OidcLoginState("state-1")
OTHER_STATE = OidcLoginState("state-2")
UNKNOWN_STATE = OidcLoginState("state-unknown")


def _transaction(nonce: str = "nonce-y") -> PendingOidcLoginTransaction:
    return PendingOidcLoginTransaction(
        expected_issuer="https://issuer.example",
        expected_nonce=nonce,
        code_verifier="verifier-z",
        redirect_uri="https://app.example/v1/session/oidc/callback",
        created_at=CREATED,
        expires_at=EXPIRES,
    )


class CountingClock:
    """Test-only clock that records how often it was read."""

    def __init__(self, value: datetime) -> None:
        self.value = value
        self.reads = 0

    def __call__(self) -> datetime:
        self.reads += 1
        return self.value


def _stored_states(store: InMemoryOidcLoginTransactions) -> set[OidcLoginState]:
    """Test-only read-only inspection of the local adapter state."""

    return set(store._transactions)  # noqa: SLF001


def _store(
    transactions: dict[OidcLoginState, PendingOidcLoginTransaction] | None = None,
    at: datetime = BEFORE_EXPIRY,
) -> tuple[InMemoryOidcLoginTransactions, CountingClock]:
    clock = CountingClock(at)
    store = InMemoryOidcLoginTransactions(
        {STATE: _transaction()} if transactions is None else transactions,
        now=clock,
    )
    return store, clock


# --- Construction ----------------------------------------------------------

def test_constructor_copies_the_input_mapping() -> None:
    source = {STATE: _transaction()}
    store = InMemoryOidcLoginTransactions(source, now=CountingClock(BEFORE_EXPIRY))

    assert _stored_states(store) == {STATE}
    assert store._transactions is not source  # noqa: SLF001


def test_later_changes_to_the_input_mapping_do_not_affect_the_adapter() -> None:
    source = {STATE: _transaction()}
    store, _clock = _store(source)

    source[OTHER_STATE] = _transaction()
    del source[STATE]

    assert _stored_states(store) == {STATE}


# --- Successful claim ------------------------------------------------------

def test_successful_claim_returns_the_stored_record() -> None:
    pending = _transaction()
    store, _clock = _store({STATE: pending})

    assert store.claim_transaction(STATE) is pending


def test_successful_claim_reads_the_clock_exactly_once() -> None:
    store, clock = _store()

    store.claim_transaction(STATE)

    assert clock.reads == 1


def test_successful_claim_removes_the_state() -> None:
    store, _clock = _store()

    store.claim_transaction(STATE)

    assert _stored_states(store) == set()


def test_second_claim_returns_none() -> None:
    store, _clock = _store()

    first = store.claim_transaction(STATE)
    second = store.claim_transaction(STATE)

    assert first is not None
    assert second is None


def test_second_claim_does_not_read_the_clock_again() -> None:
    store, clock = _store()

    store.claim_transaction(STATE)
    store.claim_transaction(STATE)

    assert clock.reads == 1


def test_returned_record_is_the_unmutated_stored_record() -> None:
    pending = _transaction()
    store, _clock = _store({STATE: pending})

    claimed = store.claim_transaction(STATE)

    assert claimed is pending
    assert claimed == _transaction()  # unchanged by the claim


# --- Unknown state ---------------------------------------------------------

def test_unknown_state_returns_none_without_reading_the_clock() -> None:
    store, clock = _store()

    assert store.claim_transaction(UNKNOWN_STATE) is None
    assert clock.reads == 0
    assert _stored_states(store) == {STATE}


# --- Expiry ----------------------------------------------------------------

def test_expired_state_returns_none() -> None:
    store, _clock = _store(at=AFTER_EXPIRY)

    assert store.claim_transaction(STATE) is None


def test_exactly_at_expiry_returns_none() -> None:
    store, _clock = _store(at=EXPIRES)

    assert store.claim_transaction(STATE) is None


def test_expired_state_is_removed() -> None:
    store, _clock = _store(at=AFTER_EXPIRY)

    store.claim_transaction(STATE)

    assert _stored_states(store) == set()


def test_second_claim_of_expired_state_stays_none_without_new_clock_read() -> None:
    store, clock = _store(at=AFTER_EXPIRY)

    first = store.claim_transaction(STATE)
    second = store.claim_transaction(STATE)

    assert [first, second] == [None, None]
    assert clock.reads == 1


def test_expired_secrets_are_no_longer_reachable_through_the_store() -> None:
    store, _clock = _store(at=AFTER_EXPIRY)

    assert store.claim_transaction(STATE) is None
    assert _stored_states(store) == set()
    # No further claim ever hands out expected_nonce or code_verifier.
    assert store.claim_transaction(STATE) is None


def test_unknown_expired_and_already_claimed_are_indistinguishable() -> None:
    unknown_store, _c1 = _store()
    expired_store, _c2 = _store(at=AFTER_EXPIRY)
    claimed_store, _c3 = _store()
    claimed_store.claim_transaction(STATE)

    outcomes = [
        unknown_store.claim_transaction(UNKNOWN_STATE),
        expired_store.claim_transaction(STATE),
        claimed_store.claim_transaction(STATE),
    ]

    assert outcomes == [None, None, None]


# --- Isolation between transactions ----------------------------------------

def test_other_transactions_are_unchanged_on_success() -> None:
    other = _transaction("other-nonce")
    store, _clock = _store({STATE: _transaction(), OTHER_STATE: other})

    store.claim_transaction(STATE)

    assert _stored_states(store) == {OTHER_STATE}
    assert store.claim_transaction(OTHER_STATE) is other


def test_other_transactions_are_unchanged_on_expiry() -> None:
    other = _transaction("other-nonce")
    store, _clock = _store(
        {STATE: _transaction(), OTHER_STATE: other}, at=AFTER_EXPIRY
    )

    store.claim_transaction(STATE)

    assert _stored_states(store) == {OTHER_STATE}


# --- Structural boundaries -------------------------------------------------

def test_adapter_is_structurally_compatible_with_the_claim_port() -> None:
    pending = _transaction()
    store, _clock = _store({STATE: pending})
    port: OidcLoginTransactionClaimStore = store

    assert port.claim_transaction(STATE) is pending


def test_claim_signature_takes_only_state() -> None:
    parameters = inspect.signature(
        InMemoryOidcLoginTransactions.claim_transaction
    ).parameters

    assert list(parameters) == ["self", "state"]


@pytest.mark.parametrize(
    "name",
    ["add_transaction", "create_transaction", "add", "create", "put", "store"],
)
def test_adapter_has_no_add_or_create_method(name: str) -> None:
    store, _clock = _store()

    assert not hasattr(store, name)


def test_module_has_no_thread_lock_or_persistence_simulation() -> None:
    source = inspect.getsource(in_memory_mod)

    for forbidden in ("threading", "Lock", "asyncio", "sqlalchemy", "open("):
        assert forbidden not in source
    assert "tombstone" not in source.lower()
