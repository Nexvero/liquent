import ast
import inspect
from datetime import UTC, datetime, timedelta

import pytest

import liquent_platform.identity.ports as ports_mod
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.ports import OidcLoginTransactionCreationStore


CREATED = datetime(2026, 7, 29, 12, tzinfo=UTC)
EXPIRES = CREATED + timedelta(minutes=10)

STATE = OidcLoginState("state-1")
OTHER_STATE = OidcLoginState("state-2")
USED_STATE = OidcLoginState("state-used")


def _transaction(nonce: str = "nonce-y") -> PendingOidcLoginTransaction:
    return PendingOidcLoginTransaction(
        expected_issuer="https://issuer.example",
        expected_nonce=nonce,
        code_verifier="verifier-z",
        redirect_uri="https://app.example/v1/session/oidc/callback",
        created_at=CREATED,
        expires_at=EXPIRES,
    )


class StubCreationStore:
    """Test-only stub modelling the atomic non-reusing creation contract.

    Alongside the pending records it keeps a secret-free set of states that were
    already used, standing in for a consumption proof or tombstone. It is not a
    production adapter.
    """

    def __init__(
        self,
        pending: dict[OidcLoginState, PendingOidcLoginTransaction] | None = None,
        used: set[OidcLoginState] | None = None,
    ) -> None:
        self._pending = dict(pending or {})
        self._used = set(used or set())

    def add_transaction(
        self,
        state: OidcLoginState,
        transaction: PendingOidcLoginTransaction,
    ) -> bool:
        if state in self._pending:
            return False  # already pending; never overwrite
        if state in self._used:
            return False  # claimed, consumed, or dropped on expiry; no reuse
        self._pending[state] = transaction
        return True

    def stored(self, state: OidcLoginState) -> PendingOidcLoginTransaction | None:
        """Test-only read-only inspection of the stored pending record."""

        return self._pending.get(state)


def _add(
    port: OidcLoginTransactionCreationStore,
    state: OidcLoginState,
    transaction: PendingOidcLoginTransaction,
) -> bool:
    return port.add_transaction(state, transaction)


# --- Successful creation ---------------------------------------------------

def test_free_state_is_stored_and_returns_true() -> None:
    store = StubCreationStore()

    assert _add(store, STATE, _transaction()) is True


def test_stored_record_is_the_exact_same_immutable_object() -> None:
    pending = _transaction()
    store = StubCreationStore()

    _add(store, STATE, pending)

    assert store.stored(STATE) is pending


def test_state_and_record_are_not_normalized_or_altered() -> None:
    raw_state = OidcLoginState("  State/MiXeD//  ")
    pending = _transaction()
    store = StubCreationStore()

    assert _add(store, raw_state, pending) is True
    assert store.stored(raw_state) is pending
    assert store.stored(raw_state) == _transaction()  # record unchanged
    # The exact state is the key; a normalized variant is not.
    assert store.stored(OidcLoginState("state/mixed/")) is None


# --- Collision rules -------------------------------------------------------

def test_already_pending_state_returns_false() -> None:
    store = StubCreationStore({STATE: _transaction()})

    assert _add(store, STATE, _transaction("second-nonce")) is False


def test_already_used_state_returns_false() -> None:
    store = StubCreationStore(used={USED_STATE})

    assert _add(store, USED_STATE, _transaction()) is False


def test_collision_does_not_overwrite_the_existing_record() -> None:
    first = _transaction("first-nonce")
    store = StubCreationStore({STATE: first})

    _add(store, STATE, _transaction("second-nonce"))

    assert store.stored(STATE) is first


def test_used_state_collision_stores_nothing() -> None:
    store = StubCreationStore(used={USED_STATE})

    _add(store, USED_STATE, _transaction())

    assert store.stored(USED_STATE) is None


def test_false_is_identical_for_pending_and_used_collisions() -> None:
    pending_store = StubCreationStore({STATE: _transaction()})
    used_store = StubCreationStore(used={USED_STATE})

    outcomes = [
        _add(pending_store, STATE, _transaction()),
        _add(used_store, USED_STATE, _transaction()),
    ]

    assert outcomes == [False, False]


def test_another_free_state_stays_storable_after_a_collision() -> None:
    store = StubCreationStore({STATE: _transaction()}, used={USED_STATE})

    assert _add(store, STATE, _transaction()) is False
    assert _add(store, USED_STATE, _transaction()) is False
    assert _add(store, OTHER_STATE, _transaction()) is True


# --- Structural boundaries -------------------------------------------------

def test_port_is_structurally_compatible() -> None:
    pending = _transaction()
    port: OidcLoginTransactionCreationStore = StubCreationStore()

    assert port.add_transaction(STATE, pending) is True


def test_signature_has_only_self_state_and_transaction() -> None:
    parameters = inspect.signature(
        OidcLoginTransactionCreationStore.add_transaction
    ).parameters

    assert list(parameters) == ["self", "state", "transaction"]


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
        "workspace_id",
        "principal",
    ],
)
def test_signature_has_no_separate_clock_or_domain_parameter(name: str) -> None:
    parameters = inspect.signature(
        OidcLoginTransactionCreationStore.add_transaction
    ).parameters

    assert name not in parameters


def test_return_annotation_is_a_plain_bool() -> None:
    annotation = inspect.signature(
        OidcLoginTransactionCreationStore.add_transaction
    ).return_annotation

    assert annotation is bool


def test_ports_module_declares_only_protocol_methods() -> None:
    # Structural, not textual: the contract docstring legitimately mentions
    # retries and tokens while ruling them out, so inspect the AST instead.
    tree = ast.parse(inspect.getsource(ports_mod))
    bodies = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]

    assert any(node.name == "add_transaction" for node in bodies)
    for node in bodies:
        statements = [
            statement
            for statement in node.body
            if not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
        ]
        # Every port method is a bare `...` declaration: no retry loop, no
        # generation, no token, trust, HTTP, or persistence logic.
        assert len(statements) == 1
        assert isinstance(statements[0], ast.Expr)
        assert isinstance(statements[0].value, ast.Constant)
        assert statements[0].value.value is Ellipsis


def test_ports_module_imports_no_library_or_framework() -> None:
    tree = ast.parse(inspect.getsource(ports_mod))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    assert all(
        module == "typing" or module.startswith("liquent_platform.")
        for module in modules
    ), modules


def test_stub_is_test_only_and_not_exported() -> None:
    import liquent_platform.identity as identity_pkg
    import liquent_platform.identity.in_memory as in_memory_mod

    assert not hasattr(ports_mod, "StubCreationStore")
    assert not hasattr(identity_pkg, "StubCreationStore")
    # The existing local claim adapter gains no creation method in this slice.
    assert not hasattr(in_memory_mod.InMemoryOidcLoginTransactions, "add_transaction")
