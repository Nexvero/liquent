"""Consumption, expiry, and real concurrency on the normative runtime database.

Everything here needs what SQLite cannot honestly provide: timezone-aware
instants, structured constraint diagnostics, row locking, and genuinely
concurrent transactions over separate connections.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence import identity_store
from liquent_platform.persistence.identity_errors import (
    ExternalIdentityStoreUnavailable,
)
from liquent_platform.persistence.identity_store import DatabaseExternalIdentities

pytestmark = pytest.mark.postgres_integration

NOW = datetime(2026, 8, 11, 12, tzinfo=UTC)
IDENTITY = ExternalIdentity(issuer="https://idp.example.test", subject="subject-1")
OTHER = ExternalIdentity(issuer="https://idp.example.test", subject="subject-2")
ADMISSION = IdentityAdmissionId("admission-1")
SECOND = IdentityAdmissionId("admission-2")
USER = UserId("user-1")


@pytest.fixture(autouse=True)
def foundation(postgres_engine: Engine) -> None:
    """Every test admission and binding references durable foundation facts."""

    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO internal_users (user_id, status) VALUES"
                " (:first, 'active'), (:second, 'active'), (:ninth, 'active')"
            ),
            {"first": b"user-1", "second": b"user-2", "ninth": b"user-9"},
        )
        connection.execute(
            text(
                "INSERT INTO workspaces (workspace_id, status)"
                " VALUES (:workspace, 'active')"
            ),
            {"workspace": b"workspace-1"},
        )


class Clock:
    def __init__(self, *moments: Any) -> None:
        self.moments = list(moments) or [NOW]
        self.calls = 0

    def __call__(self) -> Any:
        self.calls += 1
        moment = self.moments[min(self.calls - 1, len(self.moments) - 1)]
        if isinstance(moment, BaseException):
            raise moment
        return moment


def _store(engine: Engine, clock: Any = None) -> DatabaseExternalIdentities:
    return DatabaseExternalIdentities(engine, now=clock or Clock())


def _admission(
    engine: Engine,
    admission: IdentityAdmissionId = ADMISSION,
    *,
    request: str = "request-1",
    user: UserId = USER,
    expires_at: datetime | None = None,
    consumed: ExternalIdentity | None = None,
) -> None:
    """Fixture-only insert. Preparation, never a provisioning API."""

    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO identity_admissions (admission_id, provisioning_request,"
                " target_user_id, target_workspace_id, lifetime_microseconds,"
                " expires_at, consumed_at, bound_issuer, bound_subject)"
                " VALUES (:a, :p, :u, :w, :l, :e, :c, :bi, :bs)"
            ),
            {
                "a": admission.value.encode(),
                "p": request.encode(),
                "u": str(user).encode(),
                "w": b"workspace-1",
                "l": int(timedelta(hours=1) // timedelta(microseconds=1)),
                "e": expires_at or NOW + timedelta(hours=1),
                "c": NOW if consumed else None,
                "bi": consumed.issuer.encode() if consumed else None,
                "bs": consumed.subject.encode() if consumed else None,
            },
        )


def _bind(engine: Engine, identity: ExternalIdentity, user: UserId) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO external_identity_bindings (issuer, subject, user_id)"
                " VALUES (:i, :s, :u)"
            ),
            {
                "i": identity.issuer.encode(),
                "s": identity.subject.encode(),
                "u": str(user).encode(),
            },
        )


def _counts(engine: Engine) -> tuple[int, int]:
    with engine.connect() as connection:
        bindings = connection.execute(
            text("SELECT count(*) FROM external_identity_bindings")
        ).scalar_one()
        consumed = connection.execute(
            text("SELECT count(*) FROM identity_admissions WHERE consumed_at IS NOT NULL")
        ).scalar_one()
    return bindings, consumed


def _race(url: str, first: tuple[Any, ...], second: tuple[Any, ...]) -> list[Any]:
    """Two participants, separate engines, the database decides.

    The barrier only aligns the start and the lock only appends an observation;
    neither takes part in the outcome. A participant that never completed is
    recorded as a failure rather than passing as "simply did not win".
    """

    start = threading.Barrier(2)
    observations: list[tuple[str, Any, str | None]] = []
    guard = threading.Lock()

    def attempt(name: str, admission: IdentityAdmissionId, identity: ExternalIdentity) -> None:
        outcome: Any = None
        failure: str | None = None
        try:
            engine = build_engine(url)
            try:
                store = _store(engine)
                start.wait(timeout=15)
                outcome = store.consume_admission_and_bind(admission, identity)
            finally:
                engine.dispose()
        except Exception as error:
            failure = type(error).__name__
        with guard:
            observations.append((name, outcome, failure))

    threads = [
        threading.Thread(target=attempt, args=("a", *first)),
        threading.Thread(target=attempt, args=("b", *second)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert len(observations) == 2
    incomplete = [(name, failure) for name, _, failure in observations if failure]
    assert not incomplete, f"both participants must complete: {incomplete}"
    return [outcome for _, outcome, _ in observations]


# --- byte exactness ----------------------------------------------------------


@pytest.mark.parametrize(
    "identity",
    [
        ExternalIdentity(issuer="HTTPS://IDP.EXAMPLE.TEST", subject="subject-1"),
        ExternalIdentity(issuer="https://idp.example.test", subject="SUBJECT-1"),
        ExternalIdentity(issuer="https://idp.example.test ", subject="subject-1"),
        ExternalIdentity(issuer="https://idp.example.test", subject="subject-1 "),
    ],
    ids=["issuer-case", "subject-case", "issuer-space", "subject-space"],
)
def test_a_byte_difference_is_a_different_identity(
    postgres_engine: Engine, identity: ExternalIdentity
) -> None:
    _bind(postgres_engine, IDENTITY, USER)

    assert _store(postgres_engine).get_user_id(identity) is None
    assert _store(postgres_engine).get_user_id(IDENTITY) == USER


# --- sequential consumption --------------------------------------------------


def test_a_successful_consumption_binds_once_and_is_visible_elsewhere(
    postgres_engine: Engine, postgres_url: str
) -> None:
    _admission(postgres_engine)
    clock = Clock()

    assert _store(postgres_engine, clock).consume_admission_and_bind(
        ADMISSION, IDENTITY
    ) == USER

    assert clock.calls == 1
    assert _counts(postgres_engine) == (1, 1)
    observer = build_engine(postgres_url)
    try:
        assert _store(observer).get_user_id(IDENTITY) == USER
    finally:
        observer.dispose()


@pytest.mark.parametrize(
    ("prepare", "clock_calls"),
    [
        (None, 0),
        ("expired", 1),
        ("identity-bound", 0),
        ("user-bound", 0),
    ],
    ids=["unknown", "expired-exactly", "identity-already-bound", "user-already-bound"],
)
def test_a_business_refusal_leaves_the_admission_open(
    postgres_engine: Engine, prepare: str | None, clock_calls: int
) -> None:
    if prepare == "expired":
        _admission(postgres_engine, expires_at=NOW)
    elif prepare == "identity-bound":
        _admission(postgres_engine)
        _bind(postgres_engine, IDENTITY, UserId("user-9"))
    elif prepare == "user-bound":
        _admission(postgres_engine)
        _bind(postgres_engine, OTHER, USER)
    clock = Clock()

    assert _store(postgres_engine, clock).consume_admission_and_bind(
        ADMISSION, IDENTITY
    ) is None

    assert clock.calls == clock_calls
    with postgres_engine.connect() as connection:
        open_rows = connection.execute(
            text("SELECT count(*) FROM identity_admissions WHERE consumed_at IS NULL")
        ).scalar_one()
    assert open_rows == (0 if prepare is None else 1)


@pytest.mark.parametrize("identity", [IDENTITY, OTHER], ids=["exact", "different"])
def test_a_consumed_admission_repeats_only_for_the_exact_identity(
    postgres_engine: Engine, identity: ExternalIdentity
) -> None:
    _admission(postgres_engine, consumed=IDENTITY)
    _bind(postgres_engine, IDENTITY, USER)
    clock = Clock()

    result = _store(postgres_engine, clock).consume_admission_and_bind(
        ADMISSION, identity
    )

    assert result == (USER if identity == IDENTITY else None)
    assert clock.calls == 0


# PostgreSQL returns timestamptz aware, so a broken consumed instant cannot be
# stored. These read the same row through a narrowly altered projection, which
# is what the public method would receive from a corrupted store. No private
# helper is called and no production injection seam exists.
_CONSUMED_AS_TEXT = text(
    "SELECT target_user_id, expires_at, consumed_at::text AS consumed_at,"
    " bound_issuer, bound_subject FROM identity_admissions"
    " WHERE admission_id = :admission FOR UPDATE"
)
_CONSUMED_AS_NAIVE = text(
    "SELECT target_user_id, expires_at,"
    " (consumed_at AT TIME ZONE 'UTC') AS consumed_at,"
    " bound_issuer, bound_subject FROM identity_admissions"
    " WHERE admission_id = :admission FOR UPDATE"
)


@pytest.mark.parametrize(
    "projection", [None, _CONSUMED_AS_TEXT, _CONSUMED_AS_NAIVE],
    ids=["missing-binding", "consumed-at-wrong-type", "consumed-at-naive"],
)
def test_a_structurally_broken_consumed_record_is_technical(
    postgres_engine: Engine, monkeypatch: pytest.MonkeyPatch, projection: Any
) -> None:
    _admission(postgres_engine, consumed=IDENTITY)
    if projection is None:
        pass  # the consumed record simply has no binding
    else:
        _bind(postgres_engine, IDENTITY, USER)
        monkeypatch.setattr(identity_store, "_LOCK_ADMISSION", projection)
    clock = Clock()

    with pytest.raises(ExternalIdentityStoreUnavailable) as raised:
        _store(postgres_engine, clock).consume_admission_and_bind(ADMISSION, IDENTITY)

    assert raised.value.args == ("external_identity_store_unavailable",)
    assert raised.value.__cause__ is None and raised.value.__context__ is None
    assert clock.calls == 0
    for secret in (IDENTITY.issuer, IDENTITY.subject, str(USER), ADMISSION.value):
        assert secret not in str(raised.value)


@pytest.mark.parametrize(
    "clock",
    [Clock(NOW.replace(tzinfo=None)), Clock("not-a-datetime"), Clock(RuntimeError("X"))],
    ids=["naive", "wrong-type", "raising"],
)
def test_an_unusable_clock_is_technical_and_binds_nothing(
    postgres_engine: Engine, clock: Clock
) -> None:
    _admission(postgres_engine)

    with pytest.raises(ExternalIdentityStoreUnavailable) as raised:
        _store(postgres_engine, clock).consume_admission_and_bind(ADMISSION, IDENTITY)

    assert raised.value.__cause__ is None and raised.value.__context__ is None
    assert "X" not in str(raised.value)
    assert _counts(postgres_engine) == (0, 0)


@pytest.mark.parametrize(
    ("statement", "leak"),
    [
        (text("UPDATE identity_admissions SET no_such_column = :now"), "no_such_column"),
        # Valid, but deliberately hits zero rows. The admission row is already
        # locked, so a miss is a broken invariant, never ordinary concurrency.
        (
            text(
                "UPDATE identity_admissions SET consumed_at = :now,"
                " bound_issuer = :issuer, bound_subject = :subject"
                " WHERE admission_id = :admission AND consumed_at IS NOT NULL"
            ),
            "identity_admissions",
        ),
    ],
    ids=["broken-update", "zero-rows-updated"],
)
def test_a_fault_after_the_binding_insert_rolls_everything_back(
    postgres_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    statement: Any,
    leak: str,
) -> None:
    _admission(postgres_engine)
    # Break exactly the consuming UPDATE, which is the window between the
    # binding insert and the consumption inside the same transaction.
    monkeypatch.setattr(identity_store, "_CONSUME_ADMISSION", statement)
    clock = Clock()

    with pytest.raises(ExternalIdentityStoreUnavailable) as raised:
        _store(postgres_engine, clock).consume_admission_and_bind(ADMISSION, IDENTITY)

    assert raised.value.__cause__ is None and raised.value.__context__ is None
    assert leak not in str(raised.value)
    assert clock.calls == 1
    # Nothing survives: no binding, and the admission is still open.
    assert _counts(postgres_engine) == (0, 0)


# --- real concurrency --------------------------------------------------------


@pytest.mark.parametrize(
    "scenario",
    ["same-admission-same-identity", "same-admission-two-identities",
     "two-admissions-same-identity", "two-identities-same-user"],
)
def test_two_participants_race_and_the_database_decides(
    postgres_engine: Engine, postgres_url: str, scenario: str
) -> None:
    if scenario == "two-admissions-same-identity":
        _admission(postgres_engine)
        _admission(postgres_engine, SECOND, request="request-2", user=UserId("user-2"))
        first, second = (ADMISSION, IDENTITY), (SECOND, IDENTITY)
    elif scenario == "two-identities-same-user":
        _admission(postgres_engine)
        _admission(postgres_engine, SECOND, request="request-2")
        first, second = (ADMISSION, IDENTITY), (SECOND, OTHER)
    else:
        _admission(postgres_engine)
        other = IDENTITY if scenario == "same-admission-same-identity" else OTHER
        first, second = (ADMISSION, IDENTITY), (ADMISSION, other)

    results = _race(postgres_url, first, second)
    bindings, consumed = _counts(postgres_engine)

    assert bindings == 1
    if scenario == "same-admission-same-identity":
        # The loser may observe the exact idempotent repeat and see the same user.
        assert set(results) <= {USER}
        assert consumed == 1
    elif scenario == "same-admission-two-identities":
        assert sorted(result is None for result in results) == [False, True]
        assert consumed == 1
    else:
        assert sorted(result is None for result in results) == [False, True]
        # Exactly one admission was spent; the loser's stays open.
        assert consumed == 1
