"""Transactional journal for prepared and write-started promotion attempts."""

from datetime import datetime, timezone

from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.application.staging_research_index_promotion_attempt import (
    PreparedStagingResearchIndexPromotionAttempt,
    UnknownStagingResearchIndexPromotionEffect,
    WriteStartedStagingResearchIndexPromotionAttempt,
)
from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionReceipt,
)


_INSERT_ATTEMPT = text(
    "INSERT INTO staging_research_index_promotion_attempts"
    " (operation_id,actor_user_id,evidence_digest,candidate_digest,"
    "staging_origin,target_environment,created_at)"
    " VALUES (:operation,:actor,:evidence,:candidate,:origin,:target,:observed)"
)
_INSERT_EVENT = text(
    "INSERT INTO staging_research_index_promotion_attempt_events"
    " (operation_id,sequence,state,provider_receipt_id,observed_at)"
    " VALUES (:operation,:sequence,:state,NULL,:observed)"
)
_INSERT_COMMITTED = text(
    "INSERT INTO staging_research_index_promotion_attempt_events"
    " (operation_id,sequence,state,provider_receipt_id,observed_at)"
    " VALUES (:operation,3,'committed',:receipt,:observed)"
)
_INSERT_RECONCILED_COMMITTED = text(
    "INSERT INTO staging_research_index_promotion_attempt_events"
    " (operation_id,sequence,state,provider_receipt_id,observed_at)"
    " VALUES (:operation,4,'committed',:receipt,:observed)"
)
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


class StagingResearchIndexPromotionAttemptJournalUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_attempt_journal_unavailable")


class DatabaseStagingResearchIndexPromotionAttemptJournal:
    """Persist already-authorized attempt states without granting authority."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseStagingResearchIndexPromotionAttemptJournal()"

    def record_prepared(
        self,
        attempt: PreparedStagingResearchIndexPromotionAttempt,
        *,
        observed_at: datetime,
    ) -> PreparedStagingResearchIndexPromotionAttempt:
        values = self._values(attempt, observed_at)
        try:
            try:
                with self._engine.begin() as connection:
                    connection.execute(_INSERT_ATTEMPT, values)
                    connection.execute(
                        _INSERT_EVENT,
                        values | {"sequence": 1, "state": "prepared"},
                    )
                return attempt
            except IntegrityError:
                with self._engine.connect() as connection:
                    self._require_exact(connection, attempt, ["prepared"])
                return attempt
        except StagingResearchIndexPromotionAttemptJournalUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionAttemptJournalUnavailable from None

    def mark_write_started(
        self,
        attempt: PreparedStagingResearchIndexPromotionAttempt,
        *,
        observed_at: datetime,
    ) -> WriteStartedStagingResearchIndexPromotionAttempt:
        values = self._values(attempt, observed_at)
        try:
            with self._engine.begin() as connection:
                states = self._require_exact(connection, attempt)
                if states == ["prepared"]:
                    connection.execute(
                        _INSERT_EVENT,
                        values | {"sequence": 2, "state": "write_started"},
                    )
                elif states != ["prepared", "write_started"]:
                    raise StagingResearchIndexPromotionAttemptJournalUnavailable
            return WriteStartedStagingResearchIndexPromotionAttempt(attempt)
        except StagingResearchIndexPromotionAttemptJournalUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionAttemptJournalUnavailable from None

    def record_unknown(
        self,
        attempt: WriteStartedStagingResearchIndexPromotionAttempt,
        *,
        observed_at: datetime,
    ) -> UnknownStagingResearchIndexPromotionEffect:
        if type(attempt) is not WriteStartedStagingResearchIndexPromotionAttempt:
            raise StagingResearchIndexPromotionAttemptJournalUnavailable
        prepared = attempt.prepared
        values = self._values(prepared, observed_at)
        try:
            with self._engine.begin() as connection:
                states = self._require_exact(connection, prepared)
                if states == ["prepared", "write_started"]:
                    connection.execute(
                        _INSERT_EVENT,
                        values | {"sequence": 3, "state": "effect_unknown"},
                    )
                elif states != ["prepared", "write_started", "effect_unknown"]:
                    raise StagingResearchIndexPromotionAttemptJournalUnavailable
            return UnknownStagingResearchIndexPromotionEffect(attempt)
        except StagingResearchIndexPromotionAttemptJournalUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionAttemptJournalUnavailable from None

    def record_committed(
        self,
        attempt: WriteStartedStagingResearchIndexPromotionAttempt,
        receipt: StagingResearchIndexPromotionReceipt,
        *,
        observed_at: datetime,
    ) -> StagingResearchIndexPromotionReceipt:
        if (
            type(attempt) is not WriteStartedStagingResearchIndexPromotionAttempt
            or type(receipt) is not StagingResearchIndexPromotionReceipt
        ):
            raise StagingResearchIndexPromotionAttemptJournalUnavailable
        prepared = attempt.prepared
        self._require_receipt_binding(prepared, receipt)
        values = self._values(prepared, observed_at) | {
            "receipt": receipt.operation_id
        }
        try:
            with self._engine.begin() as connection:
                states = self._require_exact(
                    connection, prepared, allow_committed_receipt=True
                )
                if states == ["prepared", "write_started"]:
                    connection.execute(_INSERT_COMMITTED, values)
                elif states == ["prepared", "write_started", "committed"]:
                    events = connection.execute(
                        _SELECT_EVENTS, {"operation": prepared.operation_id}
                    ).mappings().all()
                    if events[-1]["provider_receipt_id"] != receipt.operation_id:
                        raise StagingResearchIndexPromotionAttemptJournalUnavailable
                else:
                    raise StagingResearchIndexPromotionAttemptJournalUnavailable
            return receipt
        except StagingResearchIndexPromotionAttemptJournalUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionAttemptJournalUnavailable from None

    def record_reconciled_committed(
        self,
        unknown: UnknownStagingResearchIndexPromotionEffect,
        receipt: StagingResearchIndexPromotionReceipt,
        *,
        observed_at: datetime,
    ) -> StagingResearchIndexPromotionReceipt:
        if (
            type(unknown) is not UnknownStagingResearchIndexPromotionEffect
            or type(receipt) is not StagingResearchIndexPromotionReceipt
        ):
            raise StagingResearchIndexPromotionAttemptJournalUnavailable
        prepared = unknown.attempt.prepared
        self._require_receipt_binding(prepared, receipt)
        values = self._values(prepared, observed_at) | {
            "receipt": receipt.operation_id
        }
        try:
            with self._engine.begin() as connection:
                states = self._require_exact(
                    connection, prepared, allow_committed_receipt=True
                )
                if states == ["prepared", "write_started", "effect_unknown"]:
                    connection.execute(_INSERT_RECONCILED_COMMITTED, values)
                elif states == [
                    "prepared",
                    "write_started",
                    "effect_unknown",
                    "committed",
                ]:
                    events = connection.execute(
                        _SELECT_EVENTS, {"operation": prepared.operation_id}
                    ).mappings().all()
                    if events[-1]["provider_receipt_id"] != receipt.operation_id:
                        raise StagingResearchIndexPromotionAttemptJournalUnavailable
                else:
                    raise StagingResearchIndexPromotionAttemptJournalUnavailable
            return receipt
        except StagingResearchIndexPromotionAttemptJournalUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexPromotionAttemptJournalUnavailable from None

    @staticmethod
    def _values(
        attempt: PreparedStagingResearchIndexPromotionAttempt,
        observed_at: datetime,
    ) -> dict[str, object]:
        if (
            type(attempt) is not PreparedStagingResearchIndexPromotionAttempt
            or type(observed_at) is not datetime
            or observed_at.tzinfo is None
            or observed_at.utcoffset() != timezone.utc.utcoffset(observed_at)
        ):
            raise StagingResearchIndexPromotionAttemptJournalUnavailable
        return {
            "operation": attempt.operation_id,
            "actor": str(attempt.command.actor.user_id),
            "evidence": attempt.command.evidence_digest,
            "candidate": attempt.authority.candidate_digest,
            "origin": attempt.authority.staging_origin,
            "target": attempt.authority.target_environment,
            "observed": observed_at.isoformat().replace("+00:00", "Z"),
        }

    @staticmethod
    def _require_receipt_binding(
        prepared: PreparedStagingResearchIndexPromotionAttempt,
        receipt: StagingResearchIndexPromotionReceipt,
    ) -> None:
        if (
            receipt.operation_id != prepared.operation_id
            or receipt.actor_user_id != prepared.command.actor.user_id
            or receipt.evidence_digest != prepared.command.evidence_digest
            or receipt.candidate_digest != prepared.authority.candidate_digest
            or receipt.staging_origin != prepared.authority.staging_origin
            or receipt.target_environment != prepared.authority.target_environment
        ):
            raise StagingResearchIndexPromotionAttemptJournalUnavailable

    @staticmethod
    def _require_exact(
        connection,
        attempt,
        expected_states=None,
        *,
        allow_committed_receipt: bool = False,
    ) -> list[str]:
        operation = {"operation": attempt.operation_id}
        row = connection.execute(_SELECT_ATTEMPT, operation).mappings().one_or_none()
        expected = {
            "operation_id": attempt.operation_id,
            "actor_user_id": str(attempt.command.actor.user_id),
            "evidence_digest": attempt.command.evidence_digest,
            "candidate_digest": attempt.authority.candidate_digest,
            "staging_origin": attempt.authority.staging_origin,
            "target_environment": attempt.authority.target_environment,
        }
        if row is None or any(row[key] != value for key, value in expected.items()):
            raise StagingResearchIndexPromotionAttemptJournalUnavailable
        events = connection.execute(_SELECT_EVENTS, operation).mappings().all()
        if any(
            event["provider_receipt_id"] is not None
            and not (allow_committed_receipt and event["state"] == "committed")
            for event in events
        ):
            raise StagingResearchIndexPromotionAttemptJournalUnavailable
        states = [event["state"] for event in events]
        if [event["sequence"] for event in events] != list(range(1, len(events) + 1)):
            raise StagingResearchIndexPromotionAttemptJournalUnavailable
        if expected_states is not None and states != expected_states:
            raise StagingResearchIndexPromotionAttemptJournalUnavailable
        return states
