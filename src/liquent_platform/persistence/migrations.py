"""Programmatic Alembic configuration without URLs in repository files."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


MIGRATIONS_ROOT = Path(__file__).with_name("alembic")


def migration_config(database_url: str | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_ROOT))
    if database_url is not None:
        config.attributes["database_url"] = database_url
    return config


def expected_head() -> str:
    head = ScriptDirectory.from_config(migration_config()).get_current_head()
    if head is None:
        raise RuntimeError("migration history has no head revision")
    return head
