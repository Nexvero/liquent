from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


def test_upgrade_adds_empty_attempt_and_event_journal(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'attempts.db'}")
    upgrade_to_head(str(engine.url))
    try:
        with engine.connect() as connection:
            assert connection.scalar(text(
                "SELECT count(*) FROM staging_research_index_promotion_attempts"
            )) == 0
            assert connection.scalar(text(
                "SELECT count(*) FROM staging_research_index_promotion_attempt_events"
            )) == 0
    finally:
        engine.dispose()


def test_journal_enforces_state_order_keys_and_receipt_shape(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'constraints.db'}")
    upgrade_to_head(str(engine.url))
    attempt = {
        "operation": "promotion-2707",
        "actor": "user-2707",
        "evidence": "sha256:" + "a" * 64,
        "candidate": "sha256:" + "b" * 64,
        "origin": "https://staging.liquent.ai",
        "target": "production",
        "observed": "2026-09-16T04:00:00Z",
    }
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO staging_research_index_promotion_attempts VALUES "
                "(:operation,:actor,:evidence,:candidate,:origin,:target,:observed)"
            ), attempt)
            connection.execute(text(
                "INSERT INTO staging_research_index_promotion_attempt_events VALUES "
                "(:operation,1,'prepared',NULL,:observed)"
            ), attempt)
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO staging_research_index_promotion_attempt_events VALUES "
                    "(:operation,2,'committed',NULL,:observed)"
                ), attempt)
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO staging_research_index_promotion_attempt_events VALUES "
                "(:operation,2,'write_started',NULL,:observed)"
            ), attempt)
            connection.execute(text(
                "INSERT INTO staging_research_index_promotion_attempt_events VALUES "
                "(:operation,3,'committed','provider-2707',:observed)"
            ), attempt)
        with engine.connect() as connection:
            states = connection.execute(text(
                "SELECT state FROM staging_research_index_promotion_attempt_events "
                "ORDER BY sequence"
            )).scalars().all()
        assert states == ["prepared", "write_started", "committed"]
    finally:
        engine.dispose()
