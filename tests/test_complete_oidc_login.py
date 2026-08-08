import inspect
import traceback
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from liquent_platform.application.complete_oidc_login import (
    CompletedOidcLogin,
    complete_oidc_login,
)
from liquent_platform.application.oidc_login_errors import (
    OidcLoginCompletionUnavailable,
)
from liquent_platform.application.verify_oidc_callback import VerifiedOidcCallback
from liquent_platform.identity.access import UserId, WorkspaceId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    IdentityAdmissionRecord,
)
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.in_memory import InMemoryExternalIdentities
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    SessionId,
    SessionPrincipal,
)

IDENTITY = ExternalIdentity(issuer="https://idp.example.test", subject="subject-1")
BOUND_USER = UserId("user-bound")
ADMITTED_USER = UserId("user-admitted")
ADMISSION = IdentityAdmissionId("admission-1")
RETURN_PATH = "/workspaces/w1/research"
NOW = datetime(2026, 8, 8, 12, tzinfo=UTC)
LIFETIME = timedelta(hours=8)


def _verified(**overrides: Any) -> VerifiedOidcCallback:
    values: dict[str, Any] = {
        "identity": IDENTITY,
        "admission_id": ADMISSION,
        "return_path": RETURN_PATH,
    }
    values.update(overrides)
    return VerifiedOidcCallback(**values)


class Recorder:
    """One stand-in that records its calls and replays queued results."""

    def __init__(self, *results: Any) -> None:
        self.results = list(results)
        self.calls: list[Any] = []

    def _next(self, recorded: Any) -> Any:
        self.calls.append(recorded)
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, BaseException):
            raise result
        return result

    def get_user_id(self, identity: Any) -> Any:
        return self._next(identity)

    def consume_admission_and_bind(self, admission_id: Any, identity: Any) -> Any:
        return self._next((admission_id, identity))

    def add_session(self, session_id: Any, record: Any) -> Any:
        return self._next((session_id, record))

    def __call__(self) -> Any:
        return self._next(None)


class Generator:
    def __init__(self, *faults: Any) -> None:
        self.faults = list(faults)
        self.calls: list[str] = []

    def _next(self, name: str, value: Any) -> Any:
        self.calls.append(name)
        if self.faults and isinstance(self.faults[0], BaseException):
            raise self.faults[0]
        return value

    def new_session_id(self) -> Any:
        return self._next("session_id", SessionId("session-1"))

    def new_csrf_token(self) -> str:
        return self._next("csrf_token", "csrf-1")


class Delegating:
    """Counts calls while delegating unchanged to the real adapter."""

    def __init__(self, target: Any) -> None:
        self.target = target
        self.lookups: list[Any] = []
        self.admissions: list[Any] = []

    def get_user_id(self, identity: Any) -> Any:
        self.lookups.append(identity)
        return self.target.get_user_id(identity)

    def consume_admission_and_bind(self, admission_id: Any, identity: Any) -> Any:
        self.admissions.append((admission_id, identity))
        return self.target.consume_admission_and_bind(admission_id, identity)


def _complete(**overrides: Any) -> Any:
    parts: dict[str, Any] = {
        "identity_lookup": Recorder(BOUND_USER),
        "admission_store": Recorder(ADMITTED_USER),
        "session_store": Recorder(True),
        "generator": Generator(),
        "verified": _verified(),
        "clock": Recorder(NOW),
        "lifetime": LIFETIME,
    }
    parts.update(overrides)
    return complete_oidc_login(
        parts["identity_lookup"],
        parts["admission_store"],
        parts["session_store"],
        parts["generator"],
        parts["verified"],
        clock=parts["clock"],
        lifetime=parts["lifetime"],
    ), parts


def test_an_existing_binding_is_used_without_touching_the_admission() -> None:
    lookup, admissions, store = Recorder(BOUND_USER), Recorder(ADMITTED_USER), Recorder(True)
    clock, generator = Recorder(NOW), Generator()

    result, _ = _complete(
        identity_lookup=lookup, admission_store=admissions, session_store=store,
        generator=generator, clock=clock,
    )

    assert lookup.calls == [IDENTITY]
    assert admissions.calls == []
    assert clock.calls == [None] and generator.calls == ["session_id", "csrf_token"]
    assert len(store.calls) == 1
    stored: BrowserSessionRecord = store.calls[0][1]
    assert stored.session.principal == SessionPrincipal(BOUND_USER)
    assert result.session.expires_at == NOW + LIFETIME


@pytest.mark.parametrize(
    ("lookup", "admissions", "verified"),
    [
        (Recorder(None), Recorder(ADMITTED_USER), _verified(admission_id=None)),
        (Recorder(None), Recorder(None), _verified()),
    ],
    ids=["unbound-without-admission", "admission-refuses"],
)
def test_a_business_rejection_reads_no_clock_and_creates_nothing(
    lookup: Recorder, admissions: Recorder, verified: VerifiedOidcCallback
) -> None:
    clock, generator, store = Recorder(NOW), Generator(), Recorder(True)

    result, _ = _complete(
        identity_lookup=lookup, admission_store=admissions, session_store=store,
        generator=generator, clock=clock, verified=verified,
    )

    assert result is None
    assert clock.calls == [] and generator.calls == [] and store.calls == []


def test_an_unbound_identity_is_bound_once_and_then_gets_one_session() -> None:
    lookup, admissions, store = Recorder(None), Recorder(ADMITTED_USER), Recorder(True)
    clock, generator = Recorder(NOW), Generator()

    result, _ = _complete(
        identity_lookup=lookup, admission_store=admissions, session_store=store,
        generator=generator, clock=clock,
    )

    assert len(lookup.calls) == 1
    assert admissions.calls == [(ADMISSION, IDENTITY)]
    assert clock.calls == [None] and generator.calls == ["session_id", "csrf_token"]
    assert len(store.calls) == 1
    assert store.calls[0][1].session.principal == SessionPrincipal(ADMITTED_USER)
    assert result.session.session_id == SessionId("session-1")


def test_a_session_fault_after_binding_keeps_the_binding_and_retries_nothing() -> None:
    """Proven as state through the real adapter, not as a call list."""

    identities = InMemoryExternalIdentities(
        {
            ADMISSION: IdentityAdmissionRecord(
                target_user_id=ADMITTED_USER,
                target_workspace_id=WorkspaceId("workspace-1"),
                expires_at=NOW + timedelta(hours=1),
            )
        },
        {},
        now=lambda: NOW,
    )
    assert identities.get_user_id(IDENTITY) is None
    recording, store = Delegating(identities), Recorder(False)

    with pytest.raises(OidcLoginCompletionUnavailable):
        complete_oidc_login(
            recording, recording, store, Generator(), _verified(),
            clock=lambda: NOW, lifetime=LIFETIME,
        )

    # The failing completion itself made exactly one call to each write-relevant
    # port; the idempotent store could not hide a repeated consumption.
    assert recording.lookups == [IDENTITY]
    assert recording.admissions == [(ADMISSION, IDENTITY)]
    assert len(store.calls) == 1
    # The admission was consumed and its binding survives the session fault.
    assert identities.get_user_id(IDENTITY) == ADMITTED_USER


@pytest.mark.parametrize("return_path", [RETURN_PATH, None], ids=["path", "none"])
def test_the_result_carries_the_issued_session_and_the_path_verbatim(
    return_path: str | None,
) -> None:
    store = Recorder(True)

    result, _ = _complete(session_store=store, verified=_verified(return_path=return_path))

    assert result.session.session_id == store.calls[0][0]
    assert result.return_path is return_path
    rendered = repr(result)
    assert rendered == "CompletedOidcLogin()"
    for secret in ("session-1", "csrf-1", BOUND_USER, IDENTITY.subject, "admission-1",
                   RETURN_PATH):
        assert secret not in rendered


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(seconds=-1)])
def test_a_non_positive_lifetime_fails_before_every_dependency(
    lifetime: timedelta,
) -> None:
    lookup, admissions, store = Recorder(BOUND_USER), Recorder(ADMITTED_USER), Recorder(True)
    clock, generator = Recorder(NOW), Generator()

    with pytest.raises(OidcLoginCompletionUnavailable):
        _complete(
            identity_lookup=lookup, admission_store=admissions, session_store=store,
            generator=generator, clock=clock, lifetime=lifetime,
        )

    assert lookup.calls == [] and admissions.calls == []
    assert clock.calls == [] and generator.calls == [] and store.calls == []


_DIRTY = OidcLoginCompletionUnavailable()
try:
    try:
        raise RuntimeError("INNER-DETAIL")
    except Exception:
        raise _DIRTY from None
except OidcLoginCompletionUnavailable:
    pass


@pytest.mark.parametrize(
    ("overrides", "detail", "spares_material"),
    [
        ({"identity_lookup": Recorder(RuntimeError("LOOKUP-DETAIL"))},
         "LOOKUP-DETAIL", True),
        (
            {"identity_lookup": Recorder(None),
             "admission_store": Recorder(RuntimeError("ADMISSION-DETAIL"))},
            "ADMISSION-DETAIL", True,
        ),
        ({"clock": Recorder(RuntimeError("CLOCK-DETAIL"))}, "CLOCK-DETAIL", True),
        ({"clock": Recorder("not-a-datetime")}, None, True),
        ({"clock": Recorder(NOW.replace(tzinfo=None))}, None, True),
        ({"generator": Generator(RuntimeError("GENERATOR-DETAIL"))},
         "GENERATOR-DETAIL", False),
        ({"session_store": Recorder(RuntimeError("STORE-DETAIL"))}, "STORE-DETAIL", False),
        ({"session_store": Recorder(False)}, None, False),  # SessionLifecycleConflict
        ({"identity_lookup": Recorder(_DIRTY)}, "INNER-DETAIL", True),
    ],
    ids=["lookup", "admission", "clock-raises", "clock-wrong-type", "clock-naive",
         "generator", "session-store", "session-conflict", "dirty-completion-error"],
)
def test_a_technical_fault_at_any_stage_is_neutral_and_detail_free(
    overrides: dict[str, Any], detail: str | None, spares_material: bool
) -> None:
    generator = Generator()
    with pytest.raises(OidcLoginCompletionUnavailable) as raised:
        _complete(**{"generator": generator, **overrides})

    # A fault reached before the session is built creates no session material.
    if spares_material:
        assert generator.calls == []

    assert raised.value.args == ("oidc_login_completion_unavailable",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    chain = "".join(
        traceback.format_exception(
            type(raised.value), raised.value, raised.value.__traceback__
        )
    )
    for secret in (detail, "SessionLifecycleConflict", BOUND_USER, IDENTITY.subject):
        assert secret is None or secret not in chain


def test_a_clean_completion_error_and_a_base_exception_keep_their_identity() -> None:
    clean = OidcLoginCompletionUnavailable()
    with pytest.raises(OidcLoginCompletionUnavailable) as neutral:
        _complete(identity_lookup=Recorder(clean))
    assert neutral.value is clean

    cancel = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt) as raised:
        _complete(clock=Recorder(cancel))
    assert raised.value is cancel


def test_the_result_is_frozen_slotted_and_hashable_and_the_signature_is_narrow() -> None:
    result, _ = _complete()

    with pytest.raises(FrozenInstanceError):
        result.return_path = "/elsewhere"  # type: ignore[misc]
    assert CompletedOidcLogin.__slots__ == ("session", "return_path")
    assert hash(result) == hash(CompletedOidcLogin(result.session, RETURN_PATH))
    assert list(inspect.signature(complete_oidc_login).parameters) == [
        "identity_lookup", "admission_store", "session_store", "generator",
        "verified", "clock", "lifetime",
    ]
