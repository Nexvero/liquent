"""Provisioning persistence and concurrency on the normative database."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    IdentityAdmissionProvisioningConflict,
    IdentityAdmissionStoreUnavailable,
)
from liquent_platform.persistence.identity_provisioning import (
    DatabaseIdentityAdmissionProvisioningStore,
)

pytestmark = pytest.mark.postgres_integration

NOW = datetime(2026, 8, 11, 12, tzinfo=UTC)
LIFETIME = timedelta(hours=1)
REQUEST = ProvisioningRequestId("request-1")
ADMISSION = IdentityAdmissionId("admission-1")
USER = UserId("user-1")
WORKSPACE = WorkspaceId("workspace-1")

_INSERT = text(
    "INSERT INTO identity_admissions"
    " (admission_id, provisioning_request, target_user_id,"
    " target_workspace_id, lifetime_microseconds, expires_at, consumed_at,"
    " bound_issuer, bound_subject)"
    " VALUES (:admission, :request, :user, :workspace, :lifetime, :expires_at,"
    " :consumed_at, :issuer, :subject)"
)


class Source:
    def __init__(self, value: Any) -> None:
        self.value, self.calls = value, 0

    def __call__(self) -> Any:
        self.calls += 1
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


def _store(
    engine: Engine,
    clock: Any | None = None,
    generator: Any | None = None,
) -> DatabaseIdentityAdmissionProvisioningStore:
    return DatabaseIdentityAdmissionProvisioningStore(
        engine,
        now=clock or Source(NOW),
        generate_admission_id=generator or Source(ADMISSION),
    )


def _insert(
    engine: Engine,
    *,
    request: ProvisioningRequestId = REQUEST,
    admission: IdentityAdmissionId = ADMISSION,
    user: UserId = USER,
    workspace: WorkspaceId = WORKSPACE,
    lifetime: timedelta = LIFETIME,
    consumed: bool = False,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            _INSERT,
            {
                "admission": admission.value.encode(),
                "request": request.value.encode(),
                "user": user.encode(),
                "workspace": workspace.encode(),
                "lifetime": lifetime // timedelta(microseconds=1),
                "expires_at": NOW + lifetime,
                "consumed_at": NOW if consumed else None,
                "issuer": b"https://idp.example.test" if consumed else None,
                "subject": b"subject-1" if consumed else None,
            },
        )


def _rows(engine: Engine) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        return list(
            connection.execute(
                text("SELECT * FROM identity_admissions ORDER BY admission_id")
            ).mappings()
        )


def _provision(
    store: DatabaseIdentityAdmissionProvisioningStore,
    user: UserId = USER,
    workspace: WorkspaceId = WORKSPACE,
    lifetime: timedelta = LIFETIME,
) -> IdentityAdmissionId:
    return store.provision_admission(REQUEST, user, workspace, lifetime)


def test_first_call_stores_one_exact_open_admission(postgres_engine: Engine) -> None:
    clock, generator = Source(NOW), Source(ADMISSION)

    assert _provision(_store(postgres_engine, clock, generator)) == ADMISSION

    assert (clock.calls, generator.calls) == (1, 1)
    assert _rows(postgres_engine) == [
        {
            "admission_id": b"admission-1",
            "provisioning_request": b"request-1",
            "target_user_id": b"user-1",
            "target_workspace_id": b"workspace-1",
            "lifetime_microseconds": 3_600_000_000,
            "expires_at": NOW + LIFETIME,
            "consumed_at": None,
            "bound_issuer": None,
            "bound_subject": None,
        }
    ]


def test_uncertain_commit_retry_returns_the_original_without_dependencies(
    postgres_engine: Engine,
) -> None:
    _provision(_store(postgres_engine))  # the caller did not receive this answer
    before = _rows(postgres_engine)
    clock = Source(NOW + timedelta(days=1))
    generator = Source(IdentityAdmissionId("admission-2"))

    assert _provision(_store(postgres_engine, clock, generator)) == ADMISSION
    assert (clock.calls, generator.calls) == (0, 0)
    assert _rows(postgres_engine) == before


def test_retry_after_consumption_never_reopens_the_admission(
    postgres_engine: Engine,
) -> None:
    _insert(postgres_engine, consumed=True)
    clock, generator = Source(NOW), Source(IdentityAdmissionId("admission-2"))

    assert _provision(_store(postgres_engine, clock, generator)) == ADMISSION

    row = _rows(postgres_engine)[0]
    assert (clock.calls, generator.calls) == (0, 0)
    assert (row["consumed_at"], row["bound_issuer"], row["bound_subject"]) == (
        NOW,
        b"https://idp.example.test",
        b"subject-1",
    )


@pytest.mark.parametrize(
    ("user", "workspace", "lifetime"),
    [
        (UserId("user-2"), WORKSPACE, LIFETIME),
        (USER, WorkspaceId("workspace-2"), LIFETIME),
        (USER, WORKSPACE, timedelta(minutes=30)),
    ],
    ids=["user", "workspace", "lifetime"],
)
def test_changed_business_input_is_a_clean_conflict(
    postgres_engine: Engine,
    user: UserId,
    workspace: WorkspaceId,
    lifetime: timedelta,
) -> None:
    _insert(postgres_engine)
    before = _rows(postgres_engine)
    clock, generator = Source(NOW), Source(IdentityAdmissionId("admission-2"))

    with pytest.raises(IdentityAdmissionProvisioningConflict) as rejected:
        _provision(_store(postgres_engine, clock, generator), user, workspace, lifetime)

    assert rejected.value.args == ("identity_admission_provisioning_conflict",)
    assert rejected.value.__cause__ is rejected.value.__context__ is None
    assert (clock.calls, generator.calls) == (0, 0)
    assert _rows(postgres_engine) == before


def test_generated_id_collision_is_technical_and_not_retried(
    postgres_engine: Engine,
) -> None:
    _insert(postgres_engine, request=ProvisioningRequestId("other-request"))
    generator = Source(ADMISSION)

    with pytest.raises(IdentityAdmissionStoreUnavailable) as unavailable:
        _provision(_store(postgres_engine, Source(NOW), generator))

    assert generator.calls == 1
    assert unavailable.value.args == ("identity_admission_store_unavailable",)
    assert unavailable.value.__cause__ is unavailable.value.__context__ is None
    assert len(_rows(postgres_engine)) == 1


class BarrierClock(Source):
    def __init__(self, barrier: threading.Barrier) -> None:
        super().__init__(NOW)
        self.barrier = barrier

    def __call__(self) -> datetime:
        self.barrier.wait(timeout=15)
        return super().__call__()


def _race(
    url: str, users: tuple[UserId, UserId]
) -> list[tuple[UserId, IdentityAdmissionId | None, Exception | None]]:
    barrier, guard = threading.Barrier(2), threading.Lock()
    observations: list[
        tuple[UserId, IdentityAdmissionId | None, Exception | None]
    ] = []

    def attempt(name: str, user: UserId) -> None:
        engine, result, failure = build_engine(url), None, None
        try:
            result = _provision(
                _store(
                    engine,
                    BarrierClock(barrier),
                    Source(IdentityAdmissionId(f"admission-{name}")),
                ),
                user,
            )
        except Exception as error:
            failure = error
        finally:
            engine.dispose()
        with guard:
            observations.append((user, result, failure))

    threads = [
        threading.Thread(target=attempt, args=("a", users[0])),
        threading.Thread(target=attempt, args=("b", users[1])),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert [thread.is_alive() for thread in threads] == [False, False]
    assert len(observations) == 2
    return observations


def test_concurrent_identical_requests_converge_on_one_admission(
    postgres_engine: Engine, postgres_url: str
) -> None:
    observations = _race(postgres_url, (USER, USER))

    assert [failure for _, _, failure in observations] == [None, None]
    assert len({result for _, result, _ in observations}) == 1
    assert len(_rows(postgres_engine)) == 1


def test_concurrent_different_requests_leave_the_successful_content(
    postgres_engine: Engine, postgres_url: str
) -> None:
    observations = _race(postgres_url, (USER, UserId("user-2")))

    successes = [(user, result) for user, result, error in observations if not error]
    failures = [error for _, _, error in observations if error]
    assert len(successes) == len(failures) == 1
    assert type(failures[0]) is IdentityAdmissionProvisioningConflict
    assert failures[0].__cause__ is failures[0].__context__ is None
    assert _rows(postgres_engine)[0]["target_user_id"] == successes[0][0].encode()


@pytest.mark.parametrize(
    "fault",
    ["zero", "negative", "clock", "naive", "generator", "wrong-id", "overflow"],
)
def test_invalid_input_or_dependency_fault_is_clean_unavailable(
    postgres_engine: Engine, fault: str
) -> None:
    lifetime, clock, generator = LIFETIME, Source(NOW), Source(ADMISSION)
    if fault == "zero":
        lifetime = timedelta(0)
    elif fault == "negative":
        lifetime = -timedelta(microseconds=1)
    elif fault == "clock":
        clock = Source(RuntimeError("private-clock-detail"))
    elif fault == "naive":
        clock = Source(datetime(2026, 8, 11, 12))
    elif fault == "generator":
        generator = Source(RuntimeError("private-generator-detail"))
    elif fault == "wrong-id":
        generator = Source("not-an-admission-id")
    elif fault == "overflow":
        clock = Source(datetime.max.replace(tzinfo=UTC))

    with pytest.raises(IdentityAdmissionStoreUnavailable) as unavailable:
        _provision(_store(postgres_engine, clock, generator), lifetime=lifetime)

    assert unavailable.value.args == ("identity_admission_store_unavailable",)
    assert unavailable.value.__cause__ is unavailable.value.__context__ is None
    assert "private-" not in str(unavailable.value)
    assert _rows(postgres_engine) == []


def test_exception_boundary_and_repr(postgres_engine: Engine) -> None:
    clean = IdentityAdmissionStoreUnavailable()
    with pytest.raises(IdentityAdmissionStoreUnavailable) as same:
        _provision(_store(postgres_engine, Source(clean)))
    assert same.value is clean

    class RawStop(BaseException):
        pass

    stop = RawStop()
    store = _store(postgres_engine, Source(stop))
    assert repr(store) == "DatabaseIdentityAdmissionProvisioningStore()"
    with pytest.raises(RawStop) as raised:
        _provision(store)
    assert raised.value is stop
