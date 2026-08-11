from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.migrations import migration_config


@pytest.fixture
def engine(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'authority.db'}"
    upgrade_to_head(url)
    built = build_engine(url)
    with built.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
    yield built
    built.dispose()


def test_migration_creates_exact_foundation_tables_constraints_and_foreign_keys(
    engine: object,
) -> None:
    inspector = inspect(engine)
    assert {
        "internal_users",
        "workspaces",
        "workspace_onboarding_authorities",
    } <= set(inspector.get_table_names())
    assert inspector.get_pk_constraint("internal_users")["name"] == "pk_internal_users"
    assert inspector.get_pk_constraint("workspaces")["name"] == "pk_workspaces"
    assert (
        inspector.get_pk_constraint("workspace_onboarding_authorities")[
            "constrained_columns"
        ]
        == ["user_id", "workspace_id"]
    )
    assert {
        foreign_key["name"]
        for table in (
            "external_identity_bindings",
            "identity_admissions",
            "workspace_onboarding_authorities",
        )
        for foreign_key in inspector.get_foreign_keys(table)
    } == {
        "fk_external_identity_bindings_user",
        "fk_identity_admissions_target_user",
        "fk_identity_admissions_target_workspace",
        "fk_workspace_onboarding_authorities_user",
        "fk_workspace_onboarding_authorities_workspace",
    }


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO internal_users VALUES (x'', 'active')",
        "INSERT INTO internal_users VALUES (x'75', 'revoked')",
        "INSERT INTO workspaces VALUES (x'', 'active')",
        "INSERT INTO workspaces VALUES (x'77', 'revoked')",
    ],
    ids=["empty-user", "user-status", "empty-workspace", "workspace-status"],
)
def test_invalid_foundation_rows_are_refused(engine: object, statement: str) -> None:
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:  # type: ignore[union-attr]
            connection.execute(text(statement))


def test_authority_requires_existing_targets_and_closed_status(engine: object) -> None:
    insert = text(
        "INSERT INTO workspace_onboarding_authorities"
        " (user_id, workspace_id, status) VALUES (:u, :w, :s)"
    )
    with engine.begin() as connection:  # type: ignore[union-attr]
        connection.execute(text("INSERT INTO internal_users VALUES (x'75', 'active')"))
        connection.execute(text("INSERT INTO workspaces VALUES (x'77', 'active')"))
        connection.execute(insert, {"u": b"u", "w": b"w", "s": "active"})
    for values in [
        {"u": b"missing", "w": b"w", "s": "active"},
        {"u": b"u", "w": b"missing", "s": "active"},
        {"u": b"u", "w": b"w", "s": "inactive"},
    ]:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:  # type: ignore[union-attr]
                connection.execute(insert, values)


def test_existing_identity_references_are_restrictive(engine: object) -> None:
    with engine.begin() as connection:  # type: ignore[union-attr]
        connection.execute(text("INSERT INTO internal_users VALUES (x'75', 'active')"))
        connection.execute(text("INSERT INTO workspaces VALUES (x'77', 'active')"))
        connection.execute(
            text(
                "INSERT INTO external_identity_bindings VALUES"
                " (x'69', x'73', x'75')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO identity_admissions VALUES"
                " (x'61', x'70', x'75', x'77', 1, '2026-08-12', NULL, NULL, NULL)"
            )
        )
    for deletion in [
        "DELETE FROM internal_users WHERE user_id=x'75'",
        "DELETE FROM workspaces WHERE workspace_id=x'77'",
    ]:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:  # type: ignore[union-attr]
                connection.execute(text(deletion))


def test_downgrade_removes_foundation_after_the_dependent_keys(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'downgrade.db'}"
    upgrade_to_head(url)
    command.downgrade(migration_config(url), "20260811_0002")
    engine = build_engine(url)
    try:
        inspector = inspect(engine)
        assert not {
            "internal_users",
            "workspaces",
            "workspace_onboarding_authorities",
        } & set(inspector.get_table_names())
        assert inspector.get_foreign_keys("external_identity_bindings") == []
        assert inspector.get_foreign_keys("identity_admissions") == []
    finally:
        engine.dispose()
