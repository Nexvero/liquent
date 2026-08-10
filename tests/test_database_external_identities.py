"""Portable properties of the persistent identity store, proven on SQLite.

SQLite carries no timezone offset and no structured constraint diagnostics, so
it proves only what is honestly portable: the migration, the constraints, the
byte-exact lookup, and the technical error boundary. Consumption, expiry, and
concurrency belong to the PostgreSQL suite.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.access import UserId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    ExternalIdentityStoreUnavailable,
)
from liquent_platform.persistence.identity_store import DatabaseExternalIdentities
from liquent_platform.persistence.migrate import upgrade_to_head

NOW = datetime(2026, 8, 11, 12, tzinfo=UTC)
IDENTITY = ExternalIdentity(issuer="https://idp.example.test", subject="subject-1")
USER = UserId("user-1")


@pytest.fixture
def engine(tmp_path: Path) -> Any:
    url = f"sqlite:///{tmp_path / 'identity.db'}"
    upgrade_to_head(url)
    built = build_engine(url)
    yield built
    built.dispose()


def _store(engine: Any, now: Any = lambda: NOW) -> DatabaseExternalIdentities:
    return DatabaseExternalIdentities(engine, now=now)


def _bind(engine: Any, issuer: str, subject: str, user: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO external_identity_bindings (issuer, subject, user_id)"
                " VALUES (:i, :s, :u)"
            ),
            {"i": issuer.encode(), "s": subject.encode(), "u": user.encode()},
        )


def _admission(engine: Any, **overrides: Any) -> None:
    """Fixture-only insert. This is preparation, never a provisioning API."""

    values: dict[str, Any] = {
        "a": b"admission-1",
        "p": b"request-1",
        "u": USER.encode(),
        "w": b"workspace-1",
        "l": int(timedelta(hours=1) // timedelta(microseconds=1)),
        "e": (NOW + timedelta(hours=1)).isoformat(),
        "c": None,
        "bi": None,
        "bs": None,
    }
    values.update(overrides)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO identity_admissions (admission_id, provisioning_request,"
                " target_user_id, target_workspace_id, lifetime_microseconds,"
                " expires_at, consumed_at, bound_issuer, bound_subject)"
                " VALUES (:a, :p, :u, :w, :l, :e, :c, :bi, :bs)"
            ),
            values,
        )


def test_the_migration_creates_both_tables_with_deterministic_constraints(
    engine: Any,
) -> None:
    inspector = inspect(engine)

    assert {"external_identity_bindings", "identity_admissions"} <= set(
        inspector.get_table_names()
    )
    assert (
        inspector.get_pk_constraint("external_identity_bindings")["name"]
        == "pk_external_identity_bindings"
    )
    assert [
        unique["name"]
        for unique in inspector.get_unique_constraints("external_identity_bindings")
    ] == ["uq_external_identity_bindings_user_id"]
    assert [
        unique["name"]
        for unique in inspector.get_unique_constraints("identity_admissions")
    ] == ["uq_identity_admissions_provisioning_request"]
    assert (
        inspector.get_pk_constraint("identity_admissions")["name"]
        == "pk_identity_admissions"
    )
    assert "ck_identity_admissions_consumption_group" in {
        check["name"] for check in inspector.get_check_constraints("identity_admissions")
    }


@pytest.mark.parametrize(
    ("issuer", "subject", "user"),
    [("", "s", "u"), ("i", "", "u"), ("i", "s", "")],
    ids=["issuer", "subject", "user"],
)
def test_an_empty_binding_value_is_refused_by_the_database(
    engine: Any, issuer: str, subject: str, user: str
) -> None:
    with pytest.raises(IntegrityError):
        _bind(engine, issuer, subject, user)


@pytest.mark.parametrize(
    "overrides",
    [
        {"c": NOW.isoformat(), "bi": None, "bs": None},
        {"c": None, "bi": b"i", "bs": b"s"},
        {"c": NOW.isoformat(), "bi": b"i", "bs": None},
        {"l": 0},
        {"l": -1},
    ],
    ids=["consumed-only", "bound-only", "partial", "zero-lifetime", "negative-lifetime"],
)
def test_a_broken_admission_row_is_refused_by_the_database(
    engine: Any, overrides: dict[str, Any]
) -> None:
    with pytest.raises(IntegrityError):
        _admission(engine, **overrides)


@pytest.mark.parametrize(
    "overrides",
    [{"a": b"admission-1", "p": b"other"}, {"a": b"other", "p": b"request-1"}],
    ids=["duplicate-admission-id", "duplicate-provisioning-request"],
)
def test_admission_identity_and_request_are_unique(
    engine: Any, overrides: dict[str, Any]
) -> None:
    _admission(engine)

    with pytest.raises(IntegrityError):
        _admission(engine, **overrides)


def test_one_identity_and_one_user_may_carry_only_one_binding(engine: Any) -> None:
    _bind(engine, IDENTITY.issuer, IDENTITY.subject, str(USER))

    with pytest.raises(IntegrityError):
        _bind(engine, IDENTITY.issuer, IDENTITY.subject, "user-2")
    with pytest.raises(IntegrityError):
        _bind(engine, "https://other.test", "subject-2", str(USER))


def test_the_lookup_is_byte_exact_and_answers_none_for_the_unbound(
    engine: Any,
) -> None:
    _bind(engine, IDENTITY.issuer, IDENTITY.subject, str(USER))
    store = _store(engine)

    assert store.get_user_id(IDENTITY) == USER
    # A second instance on the same database sees the committed state.
    assert _store(engine).get_user_id(IDENTITY) == USER
    for issuer, subject in [
        (IDENTITY.issuer.upper(), IDENTITY.subject),
        (IDENTITY.issuer, IDENTITY.subject.upper()),
        (IDENTITY.issuer + " ", IDENTITY.subject),
        ("https://other.test", IDENTITY.subject),
    ]:
        assert store.get_user_id(ExternalIdentity(issuer=issuer, subject=subject)) is None


def test_unreadable_stored_bytes_are_technical_and_detail_free(engine: Any) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO external_identity_bindings (issuer, subject, user_id)"
                " VALUES (:i, :s, :u)"
            ),
            {
                "i": IDENTITY.issuer.encode(),
                "s": IDENTITY.subject.encode(),
                "u": b"\xff\xfe",
            },
        )

    with pytest.raises(ExternalIdentityStoreUnavailable) as raised:
        _store(engine).get_user_id(IDENTITY)

    assert raised.value.args == ("external_identity_store_unavailable",)
    assert raised.value.__cause__ is None and raised.value.__context__ is None


def test_an_engine_fault_is_neutral_and_a_base_exception_propagates(
    engine: Any,
) -> None:
    class Broken:
        dialect = engine.dialect

        def connect(self) -> Any:
            raise RuntimeError("ENGINE-DETAIL")

        def begin(self) -> Any:
            raise RuntimeError("ENGINE-DETAIL")

    with pytest.raises(ExternalIdentityStoreUnavailable) as raised:
        _store(Broken()).get_user_id(IDENTITY)
    assert raised.value.__cause__ is None and raised.value.__context__ is None
    assert "ENGINE-DETAIL" not in str(raised.value)

    cancel = KeyboardInterrupt()

    class Cancelling:
        def connect(self) -> Any:
            raise cancel

    with pytest.raises(KeyboardInterrupt) as interrupted:
        _store(Cancelling()).get_user_id(IDENTITY)
    assert interrupted.value is cancel


def test_the_adapter_repr_carries_no_engine_dsn_clock_or_stored_value(
    engine: Any,
) -> None:
    _bind(engine, IDENTITY.issuer, IDENTITY.subject, str(USER))

    rendered = repr(_store(engine))

    assert rendered == "DatabaseExternalIdentities()"
    for secret in (str(engine.url), IDENTITY.issuer, IDENTITY.subject, str(USER)):
        assert secret not in rendered
