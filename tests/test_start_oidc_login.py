from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta

import pytest

from liquent_platform.application.oidc_login_errors import (
    OidcLoginStartConflict,
)
from liquent_platform.application.start_oidc_login import (
    StartedOidcLogin,
    start_oidc_login,
)
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.oidc_login_material import OidcLoginMaterial
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)


NOW = datetime(2026, 8, 4, 12, tzinfo=UTC)
LIFETIME = timedelta(minutes=10)
ISSUER = "https://idp.example.test"
REDIRECT_URI = "https://app.example.test/v1/oidc/callback"
ADMISSION = IdentityAdmissionId("admission-1")


class StubMaterialGenerator:
    def __init__(self) -> None:
        self.calls = 0

    def new_login_material(self) -> OidcLoginMaterial:
        self.calls += 1
        return OidcLoginMaterial(
            "generated-state",
            "generated-nonce",
            "generated-verifier",
            "generated-challenge",
        )


class StubCreationStore:
    def __init__(self, *, added: bool = True) -> None:
        self.added = added
        self.calls: list[tuple[OidcLoginState, PendingOidcLoginTransaction]] = []

    def add_transaction(
        self,
        state: OidcLoginState,
        transaction: PendingOidcLoginTransaction,
    ) -> bool:
        self.calls.append((state, transaction))
        return self.added


class ExplodingCreationStore:
    def __init__(self) -> None:
        self.calls = 0

    def add_transaction(
        self,
        state: OidcLoginState,
        transaction: PendingOidcLoginTransaction,
    ) -> bool:
        self.calls += 1
        raise RuntimeError("store unavailable")


def _start(
    store: object | None = None,
    generator: object | None = None,
    **overrides: object,
) -> StartedOidcLogin:
    arguments: dict[str, object] = {
        "expected_issuer": ISSUER,
        "redirect_uri": REDIRECT_URI,
        "now": NOW,
        "lifetime": LIFETIME,
    }
    arguments.update(overrides)
    return start_oidc_login(
        store if store is not None else StubCreationStore(),
        generator if generator is not None else StubMaterialGenerator(),
        **arguments,  # type: ignore[arg-type]
    )


# --- Success path ----------------------------------------------------------

def test_success_stores_exactly_one_pending_transaction() -> None:
    store = StubCreationStore()

    _start(store)

    assert len(store.calls) == 1


def test_material_is_generated_exactly_once() -> None:
    generator = StubMaterialGenerator()

    _start(generator=generator)

    assert generator.calls == 1


def test_stored_state_key_is_exactly_the_generated_state() -> None:
    store = StubCreationStore()

    _start(store)

    state, _pending = store.calls[0]
    assert state == OidcLoginState("generated-state")


def test_pending_record_carries_the_generated_nonce_and_verifier() -> None:
    store = StubCreationStore()

    _start(store)

    _state, pending = store.calls[0]
    assert pending.expected_nonce == "generated-nonce"
    assert pending.code_verifier == "generated-verifier"


def test_issuer_and_redirect_uri_are_kept_verbatim() -> None:
    store = StubCreationStore()

    _start(store)

    _state, pending = store.calls[0]
    assert pending.expected_issuer == ISSUER
    assert pending.redirect_uri == REDIRECT_URI


def test_created_at_is_now_and_expires_at_is_now_plus_lifetime() -> None:
    store = StubCreationStore()

    _start(store)

    _state, pending = store.calls[0]
    assert pending.created_at == NOW
    assert pending.expires_at == NOW + LIFETIME


def test_admission_id_is_bound_server_side_verbatim() -> None:
    store = StubCreationStore()

    _start(store, admission_id=ADMISSION)

    _state, pending = store.calls[0]
    assert pending.admission_id is ADMISSION


def test_return_path_is_kept_verbatim() -> None:
    store = StubCreationStore()

    _start(store, return_path="/workspaces/w-1/research")

    _state, pending = store.calls[0]
    assert pending.return_path == "/workspaces/w-1/research"


def test_admission_and_return_path_default_to_none() -> None:
    store = StubCreationStore()

    _start(store)

    _state, pending = store.calls[0]
    assert pending.admission_id is None
    assert pending.return_path is None


# --- Returned public material ----------------------------------------------

def test_result_carries_exactly_state_nonce_and_challenge() -> None:
    started = _start()

    assert started.state == "generated-state"
    assert started.nonce == "generated-nonce"
    assert started.code_challenge == "generated-challenge"


def test_result_model_has_exactly_the_three_agreed_fields() -> None:
    names = [f.name for f in fields(StartedOidcLogin)]

    assert names == ["state", "nonce", "code_challenge"]


def test_result_exposes_neither_code_verifier_nor_admission_id() -> None:
    started = _start(admission_id=ADMISSION)

    assert not hasattr(started, "code_verifier")
    assert not hasattr(started, "admission_id")
    assert "generated-verifier" not in repr(started)
    assert ADMISSION.value not in repr(started)


def test_result_repr_hides_state_and_nonce_but_shows_challenge() -> None:
    text = repr(_start())

    assert "generated-state" not in text
    assert "generated-nonce" not in text
    assert "generated-challenge" in text


def test_result_is_immutable() -> None:
    started = _start()

    with pytest.raises(FrozenInstanceError):
        started.state = "other"  # type: ignore[misc]


# --- Time bounds -----------------------------------------------------------

def test_positive_lifetime_is_accepted() -> None:
    store = StubCreationStore()

    _start(store, lifetime=timedelta(seconds=1))

    _state, pending = store.calls[0]
    assert pending.expires_at == NOW + timedelta(seconds=1)


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(seconds=-1)])
def test_non_positive_lifetime_is_rejected(lifetime: timedelta) -> None:
    with pytest.raises(ValueError, match="lifetime must be positive"):
        _start(lifetime=lifetime)


def test_naive_now_is_rejected() -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        _start(now=datetime(2026, 8, 4, 12))


@pytest.mark.parametrize(
    "overrides",
    [
        {"lifetime": timedelta(0)},
        {"now": datetime(2026, 8, 4, 12)},
    ],
)
def test_invalid_time_bounds_touch_neither_generator_nor_store(
    overrides: dict[str, object],
) -> None:
    store = StubCreationStore()
    generator = StubMaterialGenerator()

    with pytest.raises(ValueError):
        _start(store, generator, **overrides)

    assert generator.calls == 0
    assert store.calls == []


# --- Conflict --------------------------------------------------------------

def test_rejected_store_raises_the_neutral_typed_conflict() -> None:
    with pytest.raises(OidcLoginStartConflict):
        _start(StubCreationStore(added=False))


def test_conflict_carries_no_sensitive_or_existence_revealing_detail() -> None:
    with pytest.raises(OidcLoginStartConflict) as raised:
        _start(StubCreationStore(added=False), admission_id=ADMISSION)

    text = f"{raised.value!r} {raised.value!s} {raised.value.args}"
    for secret in (
        "generated-state",
        "generated-nonce",
        "generated-verifier",
        ISSUER,
        REDIRECT_URI,
        ADMISSION.value,
    ):
        assert secret not in text
    assert raised.value.code == "oidc_login_start_conflict"


def test_conflict_is_not_retried_with_new_material() -> None:
    store = StubCreationStore(added=False)
    generator = StubMaterialGenerator()

    with pytest.raises(OidcLoginStartConflict):
        _start(store, generator)

    assert generator.calls == 1
    assert len(store.calls) == 1


def test_store_failure_is_not_reinterpreted_as_a_conflict() -> None:
    store = ExplodingCreationStore()

    with pytest.raises(RuntimeError, match="store unavailable"):
        _start(store)

    assert store.calls == 1
