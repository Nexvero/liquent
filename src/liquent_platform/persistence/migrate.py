"""Controlled database migration entry point."""

from __future__ import annotations

from pathlib import Path

from alembic import command

from liquent_platform.persistence.migrations import migration_config


DATABASE_URL_SECRET_PATH = Path("/run/secrets/database_url")


def upgrade_to_head(database_url: str) -> None:
    command.upgrade(migration_config(database_url), "head")


def _load_database_url_secret(path: Path) -> str:
    try:
        database_url = path.read_text(encoding="utf-8").strip()
    except OSError:
        raise SystemExit("database_url secret is required for migrations") from None
    if not database_url:
        raise SystemExit("database_url secret is required for migrations")
    if not database_url.startswith("postgresql+psycopg://"):
        raise SystemExit("migration database_url must use postgresql+psycopg")
    return database_url


def main() -> None:
    upgrade_to_head(_load_database_url_secret(DATABASE_URL_SECRET_PATH))


if __name__ == "__main__":
    main()
