import inspect
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    IdentityAdmissionRecord,
)
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.in_memory import InMemoryExternalIdentities
from liquent_platform.identity.ports import (
    ExternalIdentityAdmissionStore,
    ExternalIdentityLookup,
)
from liquent_platform.identity.research import WorkspaceId


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)
ADMISSION = IdentityAdmissionId("admission-1")
IDENTITY = ExternalIdentity("https://issuer.example", "subject-123")
OTHER_IDENTITY = ExternalIdentity("https://issuer.example", "subject-999")
USER = UserId("user-1")
OTHER_USER = UserId("user-2")
WORKSPACE = WorkspaceId("workspace-1")


def _active(expires_at: datetime = NOW + timedelta(minutes=5)) -> IdentityAdmissionRecord:
    return IdentityAdmissionRecord(USER, WORKSPACE, expires_at)


def _consumed_record() -> IdentityAdmissionRecord:
    return IdentityAdmissionRecord(
        USER,
        WORKSPACE,
        NOW + timedelta(minutes=5),
        consumed_at=NOW - timedelta(minutes=1),
        bound_identity=IDENTITY,
    )


def _counting_clock() -> tuple[Callable[[], datetime], Callable[[], int]]:
    reads = 0

    def now() -> datetime:
        nonlocal reads
        reads += 1
        return NOW

    return now, lambda: reads


# --- Lookup ----------------------------------------------------------------

def test_lookup_known_and_unknown_without_reading_clock() -> None:
    now, reads = _counting_clock()
    adapter = InMemoryExternalIdentities({}, {IDENTITY: USER}, now=now)

    assert adapter.get_user_id(IDENTITY) == USER
    assert adapter.get_user_id(OTHER_IDENTITY) is None
    assert reads() == 0


def test_constructor_copies_input_mappings() -> None:
    # Admission targets a different user than the pre-existing binding, so the
    # copy is proven without triggering the target-collision rule.
    admissions = {
        ADMISSION: IdentityAdmissionRecord(
            OTHER_USER, WORKSPACE, NOW + timedelta(minutes=5)
        )
    }
    bindings = {IDENTITY: USER}
    adapter = InMemoryExternalIdentities(admissions, bindings, now=lambda: NOW)

    admissions.clear()
    bindings.clear()

    assert adapter.get_user_id(IDENTITY) == USER  # binding copied
    # The still-present admission binds a different identity successfully.
    assert adapter.consume_admission_and_bind(ADMISSION, OTHER_IDENTITY) == OTHER_USER


# --- consume_admission_and_bind: success -----------------------------------

def test_successful_binding_returns_target_and_lookup_resolves() -> None:
    adapter = InMemoryExternalIdentities({ADMISSION: _active()}, {}, now=lambda: NOW)

    assert adapter.consume_admission_and_bind(ADMISSION, IDENTITY) == USER
    assert adapter.get_user_id(IDENTITY) == USER


def test_success_marks_admission_consumed_with_exact_identity() -> None:
    adapter = InMemoryExternalIdentities({ADMISSION: _active()}, {}, now=lambda: NOW)

    adapter.consume_admission_and_bind(ADMISSION, IDENTITY)

    stored = adapter._admissions[ADMISSION]
    assert stored.consumed_at == NOW
    assert stored.bound_identity == IDENTITY


def test_success_reads_clock_exactly_once() -> None:
    now, reads = _counting_clock()
    adapter = InMemoryExternalIdentities({ADMISSION: _active()}, {}, now=now)

    adapter.consume_admission_and_bind(ADMISSION, IDENTITY)

    assert reads() == 1


def test_exact_repeat_is_idempotent_and_reads_no_further_clock() -> None:
    now, reads = _counting_clock()
    adapter = InMemoryExternalIdentities({ADMISSION: _active()}, {}, now=now)

    first = adapter.consume_admission_and_bind(ADMISSION, IDENTITY)
    reads_after_first = reads()
    second = adapter.consume_admission_and_bind(ADMISSION, IDENTITY)

    assert first == USER
    assert second == USER
    assert reads_after_first == 1
    assert reads() == 1  # no further clock read on the idempotent repeat


# --- consume_admission_and_bind: neutral failures --------------------------

def test_unknown_admission_returns_none_without_clock() -> None:
    now, reads = _counting_clock()
    adapter = InMemoryExternalIdentities({}, {}, now=now)

    assert adapter.consume_admission_and_bind(ADMISSION, IDENTITY) is None
    assert reads() == 0


def test_expired_admission_returns_none() -> None:
    adapter = InMemoryExternalIdentities(
        {ADMISSION: _active(NOW - timedelta(minutes=1))}, {}, now=lambda: NOW
    )

    assert adapter.consume_admission_and_bind(ADMISSION, IDENTITY) is None


def test_exactly_at_expiry_returns_none() -> None:
    adapter = InMemoryExternalIdentities(
        {ADMISSION: _active(NOW)}, {}, now=lambda: NOW
    )

    assert adapter.consume_admission_and_bind(ADMISSION, IDENTITY) is None


def test_consumed_admission_with_other_identity_none_without_clock() -> None:
    now, reads = _counting_clock()
    adapter = InMemoryExternalIdentities(
        {ADMISSION: _consumed_record()}, {IDENTITY: USER}, now=now
    )

    assert adapter.consume_admission_and_bind(ADMISSION, OTHER_IDENTITY) is None
    assert reads() == 0


def test_identity_already_bound_to_another_user_returns_none() -> None:
    adapter = InMemoryExternalIdentities(
        {ADMISSION: _active()}, {IDENTITY: OTHER_USER}, now=lambda: NOW
    )

    assert adapter.consume_admission_and_bind(ADMISSION, IDENTITY) is None


def test_target_user_already_bound_to_other_identity_returns_none() -> None:
    adapter = InMemoryExternalIdentities(
        {ADMISSION: _active()}, {OTHER_IDENTITY: USER}, now=lambda: NOW
    )

    assert adapter.consume_admission_and_bind(ADMISSION, IDENTITY) is None


def test_failure_leaves_admission_and_binding_state_unchanged() -> None:
    adapter = InMemoryExternalIdentities(
        {ADMISSION: _active(NOW - timedelta(minutes=1))}, {}, now=lambda: NOW
    )

    assert adapter.consume_admission_and_bind(ADMISSION, IDENTITY) is None
    assert adapter._admissions[ADMISSION].consumed_at is None
    assert adapter._admissions[ADMISSION].bound_identity is None
    assert adapter.get_user_id(IDENTITY) is None


# --- Structural ------------------------------------------------------------

def test_adapter_satisfies_both_ports() -> None:
    lookup: ExternalIdentityLookup = InMemoryExternalIdentities(
        {}, {IDENTITY: USER}, now=lambda: NOW
    )
    store: ExternalIdentityAdmissionStore = InMemoryExternalIdentities(
        {ADMISSION: _active()}, {}, now=lambda: NOW
    )

    assert lookup.get_user_id(IDENTITY) == USER
    assert store.consume_admission_and_bind(ADMISSION, IDENTITY) == USER


def test_no_threading_or_lock_simulation() -> None:
    source = inspect.getsource(InMemoryExternalIdentities)

    assert "threading" not in source
    assert "Lock" not in source
