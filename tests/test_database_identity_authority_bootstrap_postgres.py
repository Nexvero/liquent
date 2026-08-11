"""Normative PostgreSQL proofs for the atomic initial bootstrap."""

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
from liquent_platform.identity.bootstrap import BootstrappedIdentityAuthority
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseIdentityAuthorityBootstrapStore,
)
from liquent_platform.persistence.identity_errors import (
    IdentityAuthorityBootstrapUnavailable,
)

pytestmark = pytest.mark.postgres_integration

NOW = datetime(2026, 8, 11, 12, tzinfo=UTC)
LIFETIME = timedelta(hours=1)


class Source:
    def __init__(self, value: Any) -> None:
        self.value, self.calls = value, 0

    def __call__(self) -> Any:
        self.calls += 1
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


def _sources(suffix: str = "1") -> tuple[Source, Source, Source, Source, Source]:
    return (
        Source(UserId(f"user-{suffix}")),
        Source(WorkspaceId(f"workspace-{suffix}")),
        Source(ProvisioningRequestId(f"request-{suffix}")),
        Source(IdentityAdmissionId(f"admission-{suffix}")),
        Source(NOW),
    )


def _store(
    engine: Engine, sources: tuple[Source, Source, Source, Source, Source]
) -> DatabaseIdentityAuthorityBootstrapStore:
    user, workspace, request, admission, clock = sources
    return DatabaseIdentityAuthorityBootstrapStore(
        engine,
        generate_user_id=user,
        generate_workspace_id=workspace,
        generate_request_id=request,
        generate_admission_id=admission,
        now=clock,
        admission_lifetime=LIFETIME,
    )


def _counts(engine: Engine) -> tuple[int, int, int, int, int]:
    tables = (
        "internal_users",
        "workspaces",
        "workspace_onboarding_authorities",
        "identity_admissions",
        "identity_authority_bootstrap_decisions",
    )
    with engine.connect() as connection:
        return tuple(
            connection.scalar(text(f"SELECT count(*) FROM {table}")) for table in tables
        )  # type: ignore[return-value]


def test_first_call_commits_the_complete_exact_foundation(
    postgres_engine: Engine,
) -> None:
    sources = _sources()
    result = _store(postgres_engine, sources).bootstrap_initial_identity()

    assert result == BootstrappedIdentityAuthority(
        UserId("user-1"), WorkspaceId("workspace-1"), IdentityAdmissionId("admission-1")
    )
    assert [source.calls for source in sources] == [1, 1, 1, 1, 1]
    assert _counts(postgres_engine) == (1, 1, 1, 1, 1)
    with postgres_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT u.status AS user_status, w.status AS workspace_status,"
                " x.status AS authority_status, a.provisioning_request,"
                " a.lifetime_microseconds, a.expires_at, a.consumed_at"
                " FROM identity_authority_bootstrap_decisions d"
                " JOIN identity_admissions a ON a.admission_id=d.admission_id"
                " JOIN internal_users u ON u.user_id=a.target_user_id"
                " JOIN workspaces w ON w.workspace_id=a.target_workspace_id"
                " JOIN workspace_onboarding_authorities x"
                " ON x.user_id=u.user_id AND x.workspace_id=w.workspace_id"
            )
        ).one()
    assert tuple(row[:3]) == ("active", "active", "active")
    assert row.provisioning_request == b"request-1"
    assert row.lifetime_microseconds == 3_600_000_000
    assert row.expires_at == NOW + LIFETIME
    assert row.consumed_at is None


def test_exact_replay_uses_no_dependency_and_never_reopens(
    postgres_engine: Engine,
) -> None:
    expected = _store(postgres_engine, _sources()).bootstrap_initial_identity()
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE identity_admissions SET consumed_at=:now,"
                " bound_issuer=:issuer, bound_subject=:subject"
            ),
            {"now": NOW, "issuer": b"issuer", "subject": b"subject"},
        )
    sources = tuple(Source(AssertionError("must not run")) for _ in range(5))

    assert _store(postgres_engine, sources).bootstrap_initial_identity() == expected
    assert [source.calls for source in sources] == [0, 0, 0, 0, 0]
    with postgres_engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT consumed_at, bound_issuer, bound_subject"
                " FROM identity_admissions"
            )
        ).one() == (NOW, b"issuer", b"subject")


@pytest.mark.parametrize("table", ["internal_users", "workspaces"])
def test_foreign_nonempty_foundation_is_a_rejection_without_dependencies(
    postgres_engine: Engine, table: str
) -> None:
    column = "user_id" if table == "internal_users" else "workspace_id"
    with postgres_engine.begin() as connection:
        connection.execute(
            text(f"INSERT INTO {table} ({column}, status) VALUES (:value, 'active')"),
            {"value": b"foreign"},
        )
    sources = tuple(Source(AssertionError("must not run")) for _ in range(5))

    assert _store(postgres_engine, sources).bootstrap_initial_identity() is None
    assert [source.calls for source in sources] == [0, 0, 0, 0, 0]


@pytest.mark.parametrize(
    "failure_index",
    range(5),
    ids=["user", "workspace", "request", "admission", "clock"],
)
def test_dependency_failure_rolls_back_everything(
    postgres_engine: Engine, failure_index: int
) -> None:
    sources = list(_sources())
    sources[failure_index] = Source(RuntimeError("SECRET-DETAIL"))

    with pytest.raises(IdentityAuthorityBootstrapUnavailable) as unavailable:
        _store(postgres_engine, tuple(sources)).bootstrap_initial_identity()

    assert unavailable.value.args == ("identity_authority_bootstrap_unavailable",)
    assert unavailable.value.__cause__ is unavailable.value.__context__ is None
    assert _counts(postgres_engine) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize(
    "table",
    [
        "internal_users",
        "workspaces",
        "workspace_onboarding_authorities",
        "identity_admissions",
        "identity_authority_bootstrap_decisions",
    ],
)
def test_failure_at_each_write_stage_rolls_back_everything(
    postgres_engine: Engine, table: str
) -> None:
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION lq187_refuse_insert() RETURNS trigger"
                " LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'SECRET'; END $$"
            )
        )
        connection.execute(
            text(
                f"CREATE TRIGGER lq187_refuse BEFORE INSERT ON {table}"
                " FOR EACH ROW EXECUTE FUNCTION lq187_refuse_insert()"
            )
        )

    with pytest.raises(IdentityAuthorityBootstrapUnavailable) as unavailable:
        _store(postgres_engine, _sources()).bootstrap_initial_identity()

    assert unavailable.value.__cause__ is unavailable.value.__context__ is None
    assert _counts(postgres_engine) == (0, 0, 0, 0, 0)


def test_structurally_incomplete_decision_is_technical(
    postgres_engine: Engine,
) -> None:
    _store(postgres_engine, _sources()).bootstrap_initial_identity()
    with postgres_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM workspace_onboarding_authorities")
        )

    with pytest.raises(IdentityAuthorityBootstrapUnavailable) as unavailable:
        _store(postgres_engine, _sources("2")).bootstrap_initial_identity()
    assert unavailable.value.__cause__ is unavailable.value.__context__ is None


def test_two_concurrent_callers_return_the_same_single_foundation(
    postgres_engine: Engine, postgres_url: str
) -> None:
    barrier, guard = threading.Barrier(2), threading.Lock()
    observations: list[
        tuple[BootstrappedIdentityAuthority | None, Exception | None]
    ] = []

    def attempt(suffix: str) -> None:
        engine = build_engine(postgres_url)
        result, failure = None, None
        try:
            barrier.wait(timeout=15)
            result = _store(engine, _sources(suffix)).bootstrap_initial_identity()
        except Exception as error:
            failure = error
        finally:
            engine.dispose()
        with guard:
            observations.append((result, failure))

    threads = [
        threading.Thread(target=attempt, args=(suffix,)) for suffix in ("a", "b")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert len(observations) == 2
    assert [failure for _, failure in observations] == [None, None]
    assert observations[0][0] == observations[1][0]
    assert _counts(postgres_engine) == (1, 1, 1, 1, 1)


def test_base_exception_is_not_caught_and_no_state_survives(
    postgres_engine: Engine,
) -> None:
    raw = KeyboardInterrupt()
    sources = list(_sources())
    sources[0] = Source(raw)
    with pytest.raises(KeyboardInterrupt) as raised:
        _store(postgres_engine, tuple(sources)).bootstrap_initial_identity()
    assert raised.value is raw
    assert _counts(postgres_engine) == (0, 0, 0, 0, 0)
