"""Prove the disposable PostgreSQL path really exists (LQ-179).

No identity, admission, session, or OIDC logic: this slice only establishes that
a real server is reachable, that the repository migration runs on it, and that
two separate connections race under the server's own serialisation.
"""

from __future__ import annotations

import threading

import pytest
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, text

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrations import expected_head

pytestmark = pytest.mark.postgres_integration


def test_a_real_postgresql_server_carries_the_repository_migration(
    postgres_engine: Engine, postgres_url: str
) -> None:
    assert postgres_engine.dialect.name == "postgresql"

    with postgres_engine.connect() as connection:
        version = connection.execute(text("SELECT version()")).scalar_one()
    # A second, independent engine must see the committed migration state.
    observer = build_engine(postgres_url)
    try:
        with observer.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()
    finally:
        observer.dispose()

    assert version.startswith("PostgreSQL")
    assert revision == expected_head()
    print(f"postgres_version={version.split(' on ')[0]}")


def test_two_connections_race_and_the_server_decides_the_single_winner(
    postgres_engine: Engine, postgres_url: str
) -> None:
    """One open claim, two real transactions, exactly one winner.

    The barrier only makes both attempts start together; it decides nothing. No
    shared session and no Python lock takes part in the outcome — the conditional
    UPDATE is serialised by the row itself.
    """

    with postgres_engine.begin() as setup:
        setup.execute(
            text(
                "CREATE TABLE lq179_claim ("
                " id integer PRIMARY KEY,"
                " taken_by text)"
            )
        )
        setup.execute(text("INSERT INTO lq179_claim (id, taken_by) VALUES (1, NULL)"))

    start = threading.Barrier(2)
    winners: list[str] = []
    lock = threading.Lock()

    def attempt(name: str) -> None:
        engine = build_engine(postgres_url)
        try:
            with engine.begin() as transaction:
                start.wait(timeout=10)
                claimed = transaction.execute(
                    text(
                        "UPDATE lq179_claim SET taken_by = :name"
                        " WHERE id = 1 AND taken_by IS NULL"
                    ),
                    {"name": name},
                ).rowcount
            if claimed == 1:
                with lock:
                    winners.append(name)
        finally:
            engine.dispose()

    threads = [threading.Thread(target=attempt, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    with postgres_engine.connect() as connection:
        taken = connection.execute(text("SELECT taken_by FROM lq179_claim")).scalar_one()

    assert len(winners) == 1
    assert taken == winners[0]


def test_a_rollback_leaves_no_partial_state_and_a_commit_becomes_visible(
    postgres_engine: Engine, postgres_url: str
) -> None:
    with postgres_engine.begin() as setup:
        setup.execute(text("CREATE TABLE lq179_visibility (id integer PRIMARY KEY)"))

    observer = build_engine(postgres_url)
    try:
        with pytest.raises(RuntimeError):
            with postgres_engine.begin() as failing:
                failing.execute(text("INSERT INTO lq179_visibility (id) VALUES (1)"))
                # Uncommitted work must not be observable, and must not survive.
                with observer.connect() as peek:
                    assert peek.execute(text("SELECT count(*) FROM lq179_visibility")).scalar_one() == 0
                raise RuntimeError("abort before commit")

        with postgres_engine.begin() as committing:
            committing.execute(text("INSERT INTO lq179_visibility (id) VALUES (2)"))
        with observer.connect() as connection:
            rows = connection.execute(
                text("SELECT id FROM lq179_visibility ORDER BY id")
            ).scalars().all()
    finally:
        observer.dispose()

    assert rows == [2]
