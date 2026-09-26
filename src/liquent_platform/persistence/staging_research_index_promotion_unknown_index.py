"""Bounded read-only discovery of unknown staging promotion operations."""

from sqlalchemy import Engine, text


_LIMIT = 100
_SELECT_UNKNOWN_OPERATIONS = text(
    "SELECT attempt.operation_id"
    " FROM staging_research_index_promotion_attempts AS attempt"
    " JOIN staging_research_index_promotion_attempt_events AS event"
    " ON event.operation_id=attempt.operation_id"
    " WHERE event.state='effect_unknown'"
    " AND NOT EXISTS ("
    " SELECT 1 FROM staging_research_index_promotion_attempt_events AS later"
    " WHERE later.operation_id=event.operation_id"
    " AND later.sequence>event.sequence)"
    " ORDER BY attempt.operation_id LIMIT :limit"
)


class StagingResearchIndexPromotionUnknownIndexUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_unknown_index_unavailable")


class DatabaseStagingResearchIndexPromotionUnknownIndex:
    """Return untrusted candidate identities for exact per-operation reload."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseStagingResearchIndexPromotionUnknownIndex()"

    def list_unknown_operation_ids(self) -> tuple[str, ...]:
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    _SELECT_UNKNOWN_OPERATIONS, {"limit": _LIMIT}
                ).mappings().all()
            operation_ids = tuple(row["operation_id"] for row in rows)
            if any(type(value) is not str or not value for value in operation_ids):
                raise StagingResearchIndexPromotionUnknownIndexUnavailable
            if (
                len(operation_ids) > _LIMIT
                or len(set(operation_ids)) != len(operation_ids)
            ):
                raise StagingResearchIndexPromotionUnknownIndexUnavailable
            return operation_ids
        except StagingResearchIndexPromotionUnknownIndexUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionUnknownIndexUnavailable from None
