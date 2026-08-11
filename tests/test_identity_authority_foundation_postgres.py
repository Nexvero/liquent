from alembic import command
import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.persistence.migrations import migration_config


pytestmark = pytest.mark.postgres_integration


def test_postgresql_enforces_all_foundation_foreign_keys(
    postgres_engine: Engine,
) -> None:
    inspector = inspect(postgres_engine)
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

    with pytest.raises(IntegrityError):
        with postgres_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO external_identity_bindings"
                    " (issuer, subject, user_id) VALUES (:issuer, :subject, :user)"
                ),
                {"issuer": b"i", "subject": b"s", "user": b"u"},
            )


def test_postgresql_upgrade_fails_closed_on_an_orphaned_existing_reference(
    postgres_engine: Engine,
) -> None:
    url = postgres_engine.url.render_as_string(hide_password=False)
    command.downgrade(migration_config(url), "20260811_0002")
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO external_identity_bindings"
                " (issuer, subject, user_id) VALUES (:issuer, :subject, :user)"
            ),
            {"issuer": b"i", "subject": b"s", "user": b"orphan"},
        )

    with pytest.raises(IntegrityError):
        command.upgrade(migration_config(url), "20260811_0003")

    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260811_0002"
        )
