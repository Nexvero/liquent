import ast
import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta

import pytest

import liquent_platform.identity.ports as ports_mod
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.ports import OidcLoginTransactionClaimStore


NOW = datetime(2026, 7, 29, 12, tzinfo=UTC)
STATE = OidcLoginState("state-1")
OTHER_STATE = OidcLoginState("state-2")
EXPIRED_STATE = OidcLoginState("state-expired")


def _transaction() -> PendingOidcLoginTransaction:
    return PendingOidcLoginTransaction(
        expected_issuer="https://issuer.example",
        expected_nonce="nonce-y",
        code_verifier="verifier-z",
        redirect_uri="https://app.example/v1/session/oidc/callback",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )


# --- OidcLoginState --------------------------------------------------------

def test_valid_value_is_preserved_exactly() -> None:
    assert OidcLoginState("state-1").value == "state-1"


def test_empty_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="login state must not be empty"):
        OidcLoginState("")


@pytest.mark.parametrize(
    "value",
    ["State-MiXeD", "a/b/c", "  padded  ", "trailing/", "UPPER_lower-123"],
)
def test_case_slashes_and_whitespace_are_not_normalized(value: str) -> None:
    assert OidcLoginState(value).value == value


def test_state_is_immutable() -> None:
    state = OidcLoginState("state-1")

    with pytest.raises(FrozenInstanceError):
        state.value = "other"  # type: ignore[misc]


def test_state_is_hashable_and_usable_as_a_key() -> None:
    assert hash(OidcLoginState("state-1")) == hash(OidcLoginState("state-1"))
    assert {OidcLoginState("state-1"): 1}[OidcLoginState("state-1")] == 1


def test_state_value_is_absent_from_repr() -> None:
    text = repr(OidcLoginState("secret-state"))

    assert "secret-state" not in text


def test_state_has_exactly_the_single_value_field() -> None:
    names = [f.name for f in fields(OidcLoginState)]

    assert names == ["value"]


def test_state_has_no_transaction_admission_token_user_or_session_fields() -> None:
    names = {f.name for f in fields(OidcLoginState)}
    forbidden = {
        "transaction",
        "admission_id",
        "nonce",
        "code_verifier",
        "token",
        "id_token",
        "access_token",
        "claims",
        "issuer",
        "user_id",
        "workspace_id",
        "session",
        "session_id",
        "csrf",
    }

    assert names.isdisjoint(forbidden)


# --- Test-only stub --------------------------------------------------------

class StubClaimStore:
    """Test-only stub modelling the atomic single-use claim contract.

    It reads its own clock, fixed at construction; the caller passes no ``now``.
    An expired transaction is removed in the same step as its neutral None, so
    its secrets do not stay reachable. It is not a production adapter.
    """

    def __init__(
        self,
        transactions: dict[OidcLoginState, PendingOidcLoginTransaction] | None = None,
        now: datetime = NOW,
    ) -> None:
        self._transactions = dict(transactions or {})
        self._now = now

    def claim_transaction(
        self,
        state: OidcLoginState,
    ) -> PendingOidcLoginTransaction | None:
        pending = self._transactions.get(state)
        if pending is None:
            return None  # unknown or already claimed
        if self._now >= pending.expires_at:
            # Expired, decided by the store's own clock. The secret-bearing
            # pending state is dropped in the same step as the neutral None.
            del self._transactions[state]
            return None
        del self._transactions[state]  # fail-closed single-use consumption
        return pending

    def remaining_states(self) -> set[OidcLoginState]:
        """Test-only inspection of what pending state is left behind."""

        return set(self._transactions)


def _claim(
    port: OidcLoginTransactionClaimStore,
    state: OidcLoginState,
) -> PendingOidcLoginTransaction | None:
    return port.claim_transaction(state)


# --- Claim contract --------------------------------------------------------

def test_successful_claim_returns_the_pending_record() -> None:
    pending = _transaction()
    store = StubClaimStore({STATE: pending})

    assert _claim(store, STATE) is pending


def test_second_claim_of_the_same_state_returns_none() -> None:
    store = StubClaimStore({STATE: _transaction()})

    first = _claim(store, STATE)
    second = _claim(store, STATE)

    assert first is not None
    assert second is None


def test_unknown_state_is_neutral_none() -> None:
    store = StubClaimStore({STATE: _transaction()})

    assert _claim(store, OTHER_STATE) is None


def _expired_store() -> StubClaimStore:
    return StubClaimStore(
        {EXPIRED_STATE: _transaction()}, now=NOW + timedelta(hours=1)
    )


def test_expired_state_is_neutral_none() -> None:
    assert _claim(_expired_store(), EXPIRED_STATE) is None


def test_expired_pending_record_is_removed_fail_closed() -> None:
    store = _expired_store()

    assert _claim(store, EXPIRED_STATE) is None
    assert store.remaining_states() == set()


def test_second_claim_of_an_expired_state_stays_none() -> None:
    store = _expired_store()

    first = _claim(store, EXPIRED_STATE)
    second = _claim(store, EXPIRED_STATE)

    assert [first, second] == [None, None]


def test_expired_callback_secrets_are_no_longer_reachable_via_the_store() -> None:
    store = _expired_store()

    # Neither the claim nor any later claim hands out expected_nonce or
    # code_verifier once the transaction has expired.
    assert _claim(store, EXPIRED_STATE) is None
    assert store.remaining_states() == set()
    assert _claim(store, EXPIRED_STATE) is None


def test_unknown_expired_and_already_claimed_are_indistinguishable() -> None:
    unknown = StubClaimStore({STATE: _transaction()}).claim_transaction(OTHER_STATE)
    expired = _expired_store().claim_transaction(EXPIRED_STATE)
    claimed_store = StubClaimStore({STATE: _transaction()})
    claimed_store.claim_transaction(STATE)
    already_claimed = claimed_store.claim_transaction(STATE)

    assert [unknown, expired, already_claimed] == [None, None, None]


def test_successful_result_carries_the_callback_secrets_once() -> None:
    store = StubClaimStore({STATE: _transaction()})

    claimed = _claim(store, STATE)

    assert claimed is not None
    assert claimed.expected_nonce == "nonce-y"
    assert claimed.code_verifier == "verifier-z"
    assert store.remaining_states() == set()  # consumed fail-closed
    assert _claim(store, STATE) is None  # not available a second time


# --- Structural boundaries -------------------------------------------------

def test_port_is_structurally_compatible() -> None:
    pending = _transaction()
    port: OidcLoginTransactionClaimStore = StubClaimStore({STATE: pending})

    assert port.claim_transaction(STATE) is pending


def test_signature_has_only_self_and_state() -> None:
    parameters = inspect.signature(
        OidcLoginTransactionClaimStore.claim_transaction
    ).parameters

    assert list(parameters) == ["self", "state"]


@pytest.mark.parametrize(
    "name",
    [
        "now",
        "clock",
        "issuer",
        "expected_issuer",
        "nonce",
        "code_verifier",
        "admission_id",
        "user_id",
        "principal",
    ],
)
def test_signature_has_no_clock_or_transaction_material_parameter(name: str) -> None:
    parameters = inspect.signature(
        OidcLoginTransactionClaimStore.claim_transaction
    ).parameters

    assert name not in parameters


def test_return_annotation_is_only_pending_transaction_or_none() -> None:
    annotation = inspect.signature(
        OidcLoginTransactionClaimStore.claim_transaction
    ).return_annotation

    assert annotation == PendingOidcLoginTransaction | None


def test_claim_port_declares_only_claim_transaction_without_a_body() -> None:
    # Structural and scoped to this port only: it says nothing about the rest
    # of ports.py, its imports, other protocols, or any later addition. The
    # earlier global substring check could not tell an exclusion in a docstring
    # from real logic and blocked unrelated ports.
    tree = ast.parse(inspect.getsource(OidcLoginTransactionClaimStore))
    methods = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]

    assert [node.name for node in methods] == ["claim_transaction"]
    statements = [
        statement
        for statement in methods[0].body
        if not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        )
    ]
    # A bare `...` declaration: no adapter or execution logic in the port.
    assert len(statements) == 1
    assert isinstance(statements[0], ast.Expr)
    assert isinstance(statements[0].value, ast.Constant)
    assert statements[0].value.value is Ellipsis


def test_stub_is_test_only_and_not_exported_by_the_identity_package() -> None:
    import liquent_platform.identity as identity_pkg

    assert not hasattr(ports_mod, "StubClaimStore")
    assert not hasattr(identity_pkg, "StubClaimStore")
