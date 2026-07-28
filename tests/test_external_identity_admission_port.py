import inspect

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.ports import ExternalIdentityAdmissionStore


ADMISSION = IdentityAdmissionId("admission-1")
OTHER_ADMISSION = IdentityAdmissionId("admission-2")
EXPIRED = IdentityAdmissionId("admission-expired")
IDENTITY = ExternalIdentity("https://issuer.example", "subject-123")
OTHER_IDENTITY = ExternalIdentity("https://issuer.example", "subject-999")
TARGET = UserId("user-1")


class StubAdmissionStore:
    """Test-only stub modelling the atomic consume-and-bind contract.

    The target user is taken from the pre-issued admission; the method never
    accepts a UserId. It is not a production adapter.
    """

    def __init__(
        self,
        admissions: dict[IdentityAdmissionId, UserId] | None = None,
        expired: set[IdentityAdmissionId] | None = None,
    ) -> None:
        self._admissions = admissions or {}
        self._expired = expired or set()
        self._consumed: set[IdentityAdmissionId] = set()
        self._bindings: dict[
            ExternalIdentity, tuple[IdentityAdmissionId, UserId]
        ] = {}

    def consume_admission_and_bind(
        self,
        admission_id: IdentityAdmissionId,
        identity: ExternalIdentity,
    ) -> UserId | None:
        existing = self._bindings.get(identity)
        if existing is not None:
            bound_admission, bound_user = existing
            if bound_admission == admission_id:
                return bound_user  # exact idempotent repeat
            return None  # identity already bound elsewhere
        if admission_id not in self._admissions:
            return None  # unknown
        if admission_id in self._expired:
            return None  # expired
        if admission_id in self._consumed:
            return None  # already consumed by another operation
        target = self._admissions[admission_id]
        if any(user == target for _admission, user in self._bindings.values()):
            return None  # target user already bound to another identity
        self._consumed.add(admission_id)
        self._bindings[identity] = (admission_id, target)
        return target


def _consume(
    port: ExternalIdentityAdmissionStore,
    admission_id: IdentityAdmissionId,
    identity: ExternalIdentity,
) -> UserId | None:
    return port.consume_admission_and_bind(admission_id, identity)


def test_success_returns_internally_determined_user_id() -> None:
    store = StubAdmissionStore({ADMISSION: TARGET})

    assert _consume(store, ADMISSION, IDENTITY) == TARGET


def test_exact_repeat_is_idempotent_and_returns_same_user_id() -> None:
    store = StubAdmissionStore({ADMISSION: TARGET})

    first = _consume(store, ADMISSION, IDENTITY)
    second = _consume(store, ADMISSION, IDENTITY)

    assert first == TARGET
    assert second == TARGET


def test_unknown_admission_is_neutral_none() -> None:
    store = StubAdmissionStore({ADMISSION: TARGET})

    assert _consume(store, OTHER_ADMISSION, IDENTITY) is None


def test_expired_admission_is_neutral_none() -> None:
    store = StubAdmissionStore({EXPIRED: TARGET}, expired={EXPIRED})

    assert _consume(store, EXPIRED, IDENTITY) is None


def test_already_consumed_admission_is_neutral_none() -> None:
    store = StubAdmissionStore({ADMISSION: TARGET})

    assert _consume(store, ADMISSION, IDENTITY) == TARGET
    # Same admission, different identity -> already consumed.
    assert _consume(store, ADMISSION, OTHER_IDENTITY) is None


def test_identity_bound_to_another_user_is_neutral_none() -> None:
    store = StubAdmissionStore({ADMISSION: TARGET, OTHER_ADMISSION: TARGET})

    assert _consume(store, ADMISSION, IDENTITY) == TARGET
    # Same identity via a different admission -> already bound elsewhere.
    assert _consume(store, OTHER_ADMISSION, IDENTITY) is None


def test_target_user_collision_is_neutral_none() -> None:
    store = StubAdmissionStore({ADMISSION: TARGET, OTHER_ADMISSION: TARGET})

    assert _consume(store, ADMISSION, IDENTITY) == TARGET
    # Different identity, admission targeting an already-bound user -> collision.
    assert _consume(store, OTHER_ADMISSION, OTHER_IDENTITY) is None


def test_all_failure_cases_are_indistinguishable_none() -> None:
    outcomes = [
        StubAdmissionStore({ADMISSION: TARGET}).consume_admission_and_bind(
            OTHER_ADMISSION, IDENTITY
        ),
        StubAdmissionStore({EXPIRED: TARGET}, expired={EXPIRED}).consume_admission_and_bind(
            EXPIRED, IDENTITY
        ),
    ]

    assert outcomes == [None, None]
    assert all(outcome is None for outcome in outcomes)


def test_port_is_structurally_compatible() -> None:
    port: ExternalIdentityAdmissionStore = StubAdmissionStore({ADMISSION: TARGET})

    result = port.consume_admission_and_bind(ADMISSION, IDENTITY)

    assert result == TARGET


def test_signature_has_no_user_id_parameter() -> None:
    parameters = inspect.signature(
        ExternalIdentityAdmissionStore.consume_admission_and_bind
    ).parameters

    assert list(parameters) == ["self", "admission_id", "identity"]
    assert "user_id" not in parameters
    assert "userid" not in parameters
