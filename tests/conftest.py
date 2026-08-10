"""Disposable PostgreSQL fixtures for the marked integration path (LQ-179)."""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head

_DSN_VARIABLE = "LIQUENT_TEST_DATABASE_URL"
_REQUIRE_VARIABLE = "LIQUENT_REQUIRE_POSTGRES_TESTS"


def _required() -> bool:
    return os.environ.get(_REQUIRE_VARIABLE) == "1"


def _maintenance_url() -> str:
    """The configured DSN, or a loud failure when the path is mandatory.

    Never falls back to SQLite or an in-memory database: an unusable
    configuration must fail the run rather than silently skip the only proof of
    multi-process atomicity. Messages name the variable, never its value.
    """

    dsn = os.environ.get(_DSN_VARIABLE)
    if not dsn:
        if _required():
            pytest.fail(f"{_REQUIRE_VARIABLE}=1 but {_DSN_VARIABLE} is unset")
        pytest.skip(f"{_DSN_VARIABLE} is not set")
    if make_url(dsn).get_backend_name() != "postgresql":
        # A non-PostgreSQL backend proves nothing this path exists for.
        pytest.fail(f"{_DSN_VARIABLE} must address a postgresql backend")
    return dsn


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    """One throwaway database per test, migrated to head and dropped after.

    A dedicated database rather than a shared one: no test can see another's
    objects, and Alembic runs against exactly the isolation under test. Two
    engines built from the same URL yield genuinely separate connections, so a
    race is decided by the server and not by this process.
    """

    maintenance = _maintenance_url()
    name = f"liquent_test_{secrets.token_hex(8)}"
    admin = build_engine(maintenance)
    try:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as setup:
            setup.execute(text(f'CREATE DATABASE "{name}"'))
    except Exception:
        admin.dispose()
        # Neutral on purpose: a driver message could carry the DSN.
        pytest.fail(f"could not create a throwaway database via {_DSN_VARIABLE}")
    disposable = str(make_url(maintenance).set(database=name))
    engine = build_engine(disposable)
    try:
        upgrade_to_head(disposable)
        yield engine
    finally:
        engine.dispose()
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as drop:
            drop.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def postgres_url(postgres_engine: Engine) -> str:
    """The throwaway database's URL, for a second independent engine."""

    return postgres_engine.url.render_as_string(hide_password=False)
