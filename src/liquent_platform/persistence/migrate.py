"""Controlled database migration entry point."""

from __future__ import annotations

from pathlib import Path

from alembic import command

from liquent_platform.configuration import PlatformSettings
from liquent_platform.persistence.migrations import migration_config


def upgrade_to_head(database_url: str) -> None:
    command.upgrade(migration_config(database_url), "head")


def main() -> None:
    settings = PlatformSettings(_secrets_dir=Path("/run/secrets"))
    if settings.database_url is None:
        raise SystemExit("database_url secret is required for migrations")
    upgrade_to_head(settings.database_url.get_secret_value())


if __name__ == "__main__":
    main()
