import inspect
from datetime import UTC, datetime, timedelta

import pytest

import liquent_platform.identity.in_memory as in_memory_mod
from liquent_platform.identity.in_memory import InMemoryOidcLoginTransactions
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.ports import (
    OidcLoginTransactionClaimStore,
    OidcLoginTransactionCreationStore,
)


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


def _reserved_states(store: InMemoryOidcLoginTransactions) -> set[OidcLoginState]:
    """Test-only read-only inspection of the local reservation set."""

    return set(store._reserved_states)  # noqa: SLF001


def _stored_record(
    store: InMemoryOidcLoginTransactions, state: OidcLoginState
) -> PendingOidcLoginTransaction | None:
    """Test-only read-only inspection of one stored pending record."""

    return store._transactions.get(state)  # noqa: SLF001


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
    assert _reserved_states(store) == {STATE}


def test_initial_pending_states_are_reserved_automatically() -> None:
    store, _clock = _store({STATE: _transaction(), OTHER_STATE: _transaction()})

    assert _reserved_states(store) == {STATE, OTHER_STATE}


# --- Creation --------------------------------------------------------------

def test_free_state_is_added_and_returns_true() -> None:
    store, _clock = _store({})

    assert store.add_transaction(STATE, _transaction()) is True


def test_added_record_is_the_exact_same_immutable_object() -> None:
    pending = _transaction()
    store, _clock = _store({})

    store.add_transaction(STATE, pending)

    assert _stored_record(store, STATE) is pending


def test_added_state_is_reserved_afterwards() -> None:
    store, _clock = _store({})

    store.add_transaction(STATE, _transaction())

    assert _reserved_states(store) == {STATE}


def test_add_does_not_read_the_clock() -> None:
    store, clock = _store({})

    store.add_transaction(STATE, _transaction())
    store.add_transaction(STATE, _transaction())  # rejected, still no clock

    assert clock.reads == 0


def test_already_pending_state_is_rejected() -> None:
    store, _clock = _store()

    assert store.add_transaction(STATE, _transaction("second")) is False


def test_collision_does_not_overwrite_the_existing_record() -> None:
    first = _transaction("first-nonce")
    store, _clock = _store({STATE: first})

    store.add_transaction(STATE, _transaction("second-nonce"))

    assert _stored_record(store, STATE) is first


def test_another_free_state_stays_addable_after_a_collision() -> None:
    store, _clock = _store()

    assert store.add_transaction(STATE, _transaction()) is False
    assert store.add_transaction(OTHER_STATE, _transaction()) is True


def test_added_state_and_record_stay_exact_and_opaque() -> None:
    raw_state = OidcLoginState("  State/MiXeD//  ")
    pending = _transaction()
    store, _clock = _store({})

    assert store.add_transaction(raw_state, pending) is True
    assert _stored_record(store, raw_state) is pending
    assert _stored_record(store, raw_state) == _transaction()  # record unchanged
    # The exact state is the key; a normalized variant is not.
    assert _stored_record(store, OidcLoginState("state/mixed/")) is None


# --- Creation and claim together -------------------------------------------

def test_added_transaction_is_claimable_exactly_once() -> None:
    pending = _transaction()
    store, _clock = _store({})

    store.add_transaction(STATE, pending)

    assert store.claim_transaction(STATE) is pending
    assert store.claim_transaction(STATE) is None


def test_state_stays_reserved_after_a_successful_claim() -> None:
    store, _clock = _store()

    store.claim_transaction(STATE)

    assert _stored_states(store) == set()
    assert _reserved_states(store) == {STATE}


def test_re_add_after_a_successful_claim_is_rejected() -> None:
    store, _clock = _store()

    store.claim_transaction(STATE)

    assert store.add_transaction(STATE, _transaction("replay")) is False
    assert _stored_states(store) == set()


def test_state_stays_reserved_after_an_expired_claim() -> None:
    store, _clock = _store(at=AFTER_EXPIRY)

    store.claim_transaction(STATE)

    assert _stored_states(store) == set()
    assert _reserved_states(store) == {STATE}


def test_re_add_after_an_expired_claim_is_rejected() -> None:
    store, _clock = _store(at=AFTER_EXPIRY)

    store.claim_transaction(STATE)

    assert store.add_transaction(STATE, _transaction("replay")) is False


def test_failed_claim_of_an_unknown_state_does_not_reserve_it() -> None:
    store, _clock = _store()

    assert store.claim_transaction(UNKNOWN_STATE) is None
    assert _reserved_states(store) == {STATE}
    # A previously unknown state may still be added later.
    assert store.add_transaction(UNKNOWN_STATE, _transaction()) is True


def test_other_pending_and_reserved_states_are_unchanged_by_a_claim() -> None:
    other = _transaction("other-nonce")
    store, _clock = _store({STATE: _transaction(), OTHER_STATE: other})

    store.claim_transaction(STATE)

    assert _stored_states(store) == {OTHER_STATE}
    assert _reserved_states(store) == {STATE, OTHER_STATE}
    assert _stored_record(store, OTHER_STATE) is other


def test_other_states_are_unchanged_by_a_rejected_add() -> None:
    other = _transaction("other-nonce")
    store, _clock = _store({STATE: _transaction(), OTHER_STATE: other})

    store.add_transaction(STATE, _transaction("second"))

    assert _stored_states(store) == {STATE, OTHER_STATE}
    assert _reserved_states(store) == {STATE, OTHER_STATE}
    assert _stored_record(store, OTHER_STATE) is other


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


def test_adapter_is_structurally_compatible_with_the_creation_port() -> None:
    store, _clock = _store({})
    port: OidcLoginTransactionCreationStore = store

    assert port.add_transaction(STATE, _transaction()) is True


def test_one_instance_satisfies_both_ports() -> None:
    store, _clock = _store({})
    creation: OidcLoginTransactionCreationStore = store
    claim: OidcLoginTransactionClaimStore = store
    pending = _transaction()

    assert creation.add_transaction(STATE, pending) is True
    assert claim.claim_transaction(STATE) is pending


def test_claim_signature_takes_only_state() -> None:
    parameters = inspect.signature(
        InMemoryOidcLoginTransactions.claim_transaction
    ).parameters

    assert list(parameters) == ["self", "state"]


def test_add_signature_takes_only_state_and_transaction() -> None:
    parameters = inspect.signature(
        InMemoryOidcLoginTransactions.add_transaction
    ).parameters

    assert list(parameters) == ["self", "state", "transaction"]


@pytest.mark.parametrize(
    "name",
    ["create_transaction", "add", "create", "put", "store", "reserved_states"],
)
def test_adapter_has_no_further_management_or_inspection_api(name: str) -> None:
    # add_transaction is the one creation entry point (LQ-143); nothing beyond
    # the two port methods is public.
    store, _clock = _store()

    assert not hasattr(store, name)


def test_module_has_no_thread_lock_or_persistence_simulation() -> None:
    source = inspect.getsource(in_memory_mod)

    for forbidden in ("threading", "Lock", "asyncio", "sqlalchemy", "open("):
        assert forbidden not in source
    assert "tombstone" not in source.lower()
