"""Read-only reconstruction of durable unknown staging promotion attempts."""

import re

from sqlalchemy import Engine, text

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionCommand,
)
from liquent_platform.application.staging_research_index_promotion_attempt import (
    PreparedStagingResearchIndexPromotionAttempt,
    UnknownStagingResearchIndexPromotionEffect,
    WriteStartedStagingResearchIndexPromotionAttempt,
)
from liquent_platform.application.staging_research_index_promotion_authority import (
    CurrentStagingResearchIndexPromotionAuthority,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import SessionPrincipal


_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,255}\Z")
_SELECT_ATTEMPT = text(
    "SELECT operation_id,actor_user_id,evidence_digest,candidate_digest,"
    "staging_origin,target_environment FROM staging_research_index_promotion_attempts"
    " WHERE operation_id=:operation"
)
_SELECT_EVENTS = text(
    "SELECT sequence,state,provider_receipt_id"
    " FROM staging_research_index_promotion_attempt_events"
    " WHERE operation_id=:operation ORDER BY sequence"
)


class StagingResearchIndexPromotionUnknownReaderUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_unknown_reader_unavailable")


class DatabaseStagingResearchIndexPromotionUnknownReader:
    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseStagingResearchIndexPromotionUnknownReader()"

    def resolve_unknown(
        self, operation_id: str
    ) -> UnknownStagingResearchIndexPromotionEffect | None:
        try:
            if type(operation_id) is not str or _OPAQUE.fullmatch(operation_id) is None:
                raise StagingResearchIndexPromotionUnknownReaderUnavailable
            operation = {"operation": operation_id}
            with self._engine.connect() as connection:
                row = connection.execute(
                    _SELECT_ATTEMPT, operation
                ).mappings().one_or_none()
                if row is None:
                    return None
                events = connection.execute(_SELECT_EVENTS, operation).mappings().all()
            sequences = [event["sequence"] for event in events]
            states = [event["state"] for event in events]
            if sequences != list(range(1, len(events) + 1)):
                raise StagingResearchIndexPromotionUnknownReaderUnavailable
            allowed = {
                ("prepared",),
                ("prepared", "write_started"),
                ("prepared", "write_started", "effect_unknown"),
                ("prepared", "write_started", "committed"),
                ("prepared", "write_started", "effect_unknown", "committed"),
            }
            if tuple(states) not in allowed:
                raise StagingResearchIndexPromotionUnknownReaderUnavailable
            for event in events:
                receipt = event["provider_receipt_id"]
                if (event["state"] == "committed") != (receipt is not None):
                    raise StagingResearchIndexPromotionUnknownReaderUnavailable
            if states != ["prepared", "write_started", "effect_unknown"]:
                return None
            actor = SessionPrincipal(UserId(row["actor_user_id"]))
            command = StagingResearchIndexPromotionCommand(
                actor, row["evidence_digest"]
            )
            authority = CurrentStagingResearchIndexPromotionAuthority(
                actor.user_id,
                row["candidate_digest"],
                row["staging_origin"],
                row["target_environment"],
            )
            prepared = PreparedStagingResearchIndexPromotionAttempt(
                row["operation_id"], command, authority
            )
            return UnknownStagingResearchIndexPromotionEffect(
                WriteStartedStagingResearchIndexPromotionAttempt(prepared)
            )
        except StagingResearchIndexPromotionUnknownReaderUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionUnknownReaderUnavailable from None
