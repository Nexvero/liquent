"""Persistent state resolution and single-read outcome finalization."""

from __future__ import annotations

from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import (
    FinalizedReleasePublication,
    FinalizedReleasePublicationRecovery,
    ReleasePublicationAttemptId,
    ReleasePublicationExecutionId,
    ReleasePublicationFinalStatus,
    ReleasePublicationReconciliationKind,
    ReleasePublicationWorkRequest,
    ReleasePublicationWorkResultKind,
    ReleasePublicationWorkState,
    ReleasePublicationWorkStateKind,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationCurrentOutcomeFinalizeUnavailable,
    ReleasePublicationWorkStateUnavailable,
)


_STATE = text(
    "SELECT execution.handoff_id,execution.publisher_authority_id,"
    " execution.channel_id,execution.channel_revision_id,execution.status,"
    " attempt.attempt_id,attempt.attempt_number,attempt.status AS attempt_status,"
    " attempt.finished_at,recovery.kind AS recovery_kind,"
    " recovery.current_authority,receipt.status AS receipt_status"
    " FROM release_publication_executions execution"
    " JOIN release_publication_execution_attempts attempt"
    " ON attempt.execution_id=execution.execution_id"
    " LEFT JOIN release_publication_recovery_decisions recovery"
    " ON recovery.execution_id=execution.execution_id"
    " AND recovery.attempt_id=attempt.attempt_id"
    " LEFT JOIN release_publication_receipt_reconciliations receipt"
    " ON receipt.execution_id=execution.execution_id"
    " AND receipt.attempt_id=attempt.attempt_id"
    " WHERE execution.execution_id=:execution ORDER BY attempt.attempt_number"
)


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleasePublicationWorkStateUnavailable
    try:
        return bytes(value).decode("utf-8")
    except UnicodeError:
        raise ReleasePublicationWorkStateUnavailable from None


class DatabaseReleasePublicationWorkStateLookup:
    """Bind one closed request to its complete current execution state."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationWorkStateLookup()"

    def get_work_state(self, request):
        try:
            if type(request) is not ReleasePublicationWorkRequest:
                raise ReleasePublicationWorkStateUnavailable
            with self._engine.connect() as connection:
                rows = connection.execute(
                    _STATE, {"execution": request.execution_id.value.encode()}
                ).all()
            if not rows:
                return None
            if len(rows) not in {1, 2}:
                raise ReleasePublicationWorkStateUnavailable
            if not self._bound(request, rows):
                return ReleasePublicationWorkState(
                    ReleasePublicationWorkStateKind.NOT_ACTIONABLE
                )
            return self._state(rows)
        except ReleasePublicationWorkStateUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationWorkStateUnavailable

    @staticmethod
    def _bound(request, rows):
        expected = (
            request.handoff_id.value,
            request.publisher_authority_id.value,
            request.channel_id.value,
            request.expected_channel_revision.value,
        )
        for row in rows:
            actual = tuple(_decode(value) for value in (
                row.handoff_id,
                row.publisher_authority_id,
                row.channel_id,
                row.channel_revision_id,
            ))
            if actual != expected:
                return False
        return True

    def _state(self, rows):
        execution_status = rows[0].status
        if any(row.status != execution_status for row in rows):
            raise ReleasePublicationWorkStateUnavailable
        terminal = {
            "published": ReleasePublicationWorkResultKind.PUBLISHED,
            "published_reassessment_required": (
                ReleasePublicationWorkResultKind.PUBLISHED_REASSESSMENT_REQUIRED
            ),
            "not_published": ReleasePublicationWorkResultKind.NOT_PUBLISHED,
            "publication_conflict": (
                ReleasePublicationWorkResultKind.PUBLICATION_CONFLICT
            ),
        }
        if execution_status in terminal:
            self._terminal(rows, execution_status)
            return ReleasePublicationWorkState(
                ReleasePublicationWorkStateKind.TERMINAL,
                terminal_result=terminal[execution_status],
            )
        if execution_status not in {"prepared", "outcome_unknown"}:
            raise ReleasePublicationWorkStateUnavailable
        self._numbers(rows)
        current = rows[-1]
        attempt_id = ReleasePublicationAttemptId(_decode(current.attempt_id))
        if len(rows) == 2:
            self._recovered_first(rows[0])
            number = 2
        else:
            number = 1
        if execution_status == "outcome_unknown":
            if (
                current.attempt_status == "reconciled"
                and current.finished_at is not None
                and current.recovery_kind == "conflict"
            ):
                return ReleasePublicationWorkState(
                    ReleasePublicationWorkStateKind.TERMINAL,
                    terminal_result=(
                        ReleasePublicationWorkResultKind.PUBLICATION_CONFLICT
                    ),
                )
            if current.attempt_status != "outcome_unknown" or current.finished_at is not None:
                raise ReleasePublicationWorkStateUnavailable
            kind = (
                ReleasePublicationWorkStateKind.ATTEMPT_ONE_UNKNOWN
                if number == 1
                else ReleasePublicationWorkStateKind.ATTEMPT_TWO_UNKNOWN
            )
            return ReleasePublicationWorkState(kind, attempt_id)
        if number == 1 and current.attempt_status == "reconciled":
            self._recovered_first(current)
            return ReleasePublicationWorkState(
                ReleasePublicationWorkStateKind.ATTEMPT_ONE_ABSENCE_RECOVERED,
                attempt_id,
            )
        if current.attempt_status not in {"prepared", "write_started"}:
            raise ReleasePublicationWorkStateUnavailable
        if current.finished_at is not None:
            raise ReleasePublicationWorkStateUnavailable
        kind = (
            ReleasePublicationWorkStateKind.ATTEMPT_ONE_PREPARED
            if number == 1
            else ReleasePublicationWorkStateKind.ATTEMPT_TWO_PREPARED
        )
        return ReleasePublicationWorkState(kind, attempt_id)

    @staticmethod
    def _numbers(rows):
        if [row.attempt_number for row in rows] != list(range(1, len(rows) + 1)):
            raise ReleasePublicationWorkStateUnavailable

    @staticmethod
    def _recovered_first(row):
        if (
            row.attempt_number != 1
            or row.attempt_status != "reconciled"
            or row.finished_at is None
            or row.recovery_kind != "absence_confirmed"
            or row.receipt_status is not None
            or row.current_authority not in {True, False, 0, 1}
        ):
            raise ReleasePublicationWorkStateUnavailable

    @staticmethod
    def _terminal(rows, execution_status):
        current = rows[-1]
        if current.attempt_status != "reconciled" or current.finished_at is None:
            raise ReleasePublicationWorkStateUnavailable
        published = execution_status in {
            "published", "published_reassessment_required"
        }
        if published != (current.receipt_status == execution_status):
            raise ReleasePublicationWorkStateUnavailable
        if not published and current.recovery_kind not in {
            "absence_confirmed", "conflict"
        }:
            raise ReleasePublicationWorkStateUnavailable


class DatabaseReleasePublicationCurrentOutcomeFinalizer:
    """Reconcile once, then commit through exactly one matching finalizer."""

    __slots__ = ("_reconciliation", "_receipt", "_recovery")

    def __init__(self, *, reconciliation, receipt_finalizer, recovery_finalizer):
        self._reconciliation = reconciliation
        self._receipt = receipt_finalizer
        self._recovery = recovery_finalizer

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationCurrentOutcomeFinalizer()"

    def finalize_current_outcome(self, execution_id, attempt_id):
        try:
            if (
                type(execution_id) is not ReleasePublicationExecutionId
                or type(attempt_id) is not ReleasePublicationAttemptId
            ):
                raise ReleasePublicationCurrentOutcomeFinalizeUnavailable
            existing = self._receipt.existing_finalization(
                execution_id, attempt_id
            )
            if existing is not None:
                if type(existing) is not FinalizedReleasePublication:
                    raise ReleasePublicationCurrentOutcomeFinalizeUnavailable
                return existing
            existing = self._recovery.existing_finalization(
                execution_id, attempt_id
            )
            if existing is not None:
                if type(existing) is not FinalizedReleasePublicationRecovery:
                    raise ReleasePublicationCurrentOutcomeFinalizeUnavailable
                return existing
            outcome = self._reconciliation.reconcile_unknown_outcome(
                execution_id, attempt_id
            )
            if outcome is None:
                return None
            if outcome.kind is ReleasePublicationReconciliationKind.PUBLISHED_CONFIRMED:
                result = self._receipt.commit_reconciled_outcome(
                    execution_id, attempt_id, outcome
                )
                if result is not None and type(result) is not FinalizedReleasePublication:
                    raise ReleasePublicationCurrentOutcomeFinalizeUnavailable
                return result
            result = self._recovery.commit_reconciled_outcome(
                execution_id, attempt_id, outcome
            )
            if result is not None and type(result) is not FinalizedReleasePublicationRecovery:
                raise ReleasePublicationCurrentOutcomeFinalizeUnavailable
            return result
        except ReleasePublicationCurrentOutcomeFinalizeUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationCurrentOutcomeFinalizeUnavailable
