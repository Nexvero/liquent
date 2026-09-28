"""Atomic persistent write claims for supervisor control-directory cleanup."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    CleanupManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    ManifestHandoffSupervisorControlDirectoryCleanupClearanceId,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_execution import (
    ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup,
    ClaimedManifestHandoffSupervisorControlDirectoryCleanup,
    ManifestHandoffSupervisorControlDirectoryCleanupPreflightId,
    ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId,
    PreparedManifestHandoffSupervisorControlDirectoryCleanup,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_cleanup_clearance_creation import (
    DatabaseManifestHandoffSupervisorCleanupClearanceCreation,
)


_ATTEMPT = text(
    "SELECT * FROM manifest_handoff_supervisor_control_cleanup_attempts WHERE attempt_id=:attempt"
)
_CLEARANCE = text(
    "SELECT * FROM manifest_handoff_supervisor_cleanup_clearances WHERE attempt_id=:attempt"
)
_CLAIM = text(
    "SELECT * FROM manifest_handoff_supervisor_control_cleanup_write_claims WHERE attempt_id=:attempt"
)
_CLAIM_VIEW = text(
    "SELECT claim.*,attempt.state,attempt.started_at,attempt.write_claimed_at,attempt.outcome"
    " FROM manifest_handoff_supervisor_control_cleanup_write_claims claim"
    " JOIN manifest_handoff_supervisor_control_cleanup_attempts attempt"
    " ON attempt.attempt_id=claim.attempt_id AND attempt.directory_id=claim.directory_id"
    " WHERE claim.attempt_id=:attempt"
)


def _encode(value: object) -> bytes:
    raw = value.value if hasattr(value, "value") else value
    if type(raw) is not str or not raw:
        raise ManifestHandoffRegistryUnavailable
    return raw.encode("utf-8")


def _decode(value: object) -> str:
    try:
        if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
            raise ManifestHandoffRegistryUnavailable
        result = bytes(value).decode("utf-8")
    except UnicodeError:
        raise ManifestHandoffRegistryUnavailable from None
    if not result:
        raise ManifestHandoffRegistryUnavailable
    return result


def _utc(value: object) -> datetime:
    if type(value) is str:
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            raise ManifestHandoffRegistryUnavailable from None
    if type(value) is not datetime:
        raise ManifestHandoffRegistryUnavailable
    value = value.replace(tzinfo=value.tzinfo or timezone.utc)
    if value.utcoffset() != timedelta(0):
        raise ManifestHandoffRegistryUnavailable
    return value


class DatabaseManifestHandoffSupervisorControlDirectoryCleanupWriteClaims:
    """Claim one current cleared and physically prepared attempt exactly once."""

    __slots__ = ("_engine", "_clock", "_claim", "_clearances")

    def __init__(
        self,
        engine: Engine,
        *,
        clock: Callable[[], datetime] | None = None,
        claim_id_generator: Callable[[], str] | None = None,
    ) -> None:
        if (
            not isinstance(engine, Engine)
            or (clock is not None and not callable(clock))
            or (claim_id_generator is not None and not callable(claim_id_generator))
        ):
            raise ManifestHandoffRegistryUnavailable
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._claim = claim_id_generator or (lambda: secrets.token_hex(32))
        self._clearances = DatabaseManifestHandoffSupervisorCleanupClearanceCreation(engine)

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorControlDirectoryCleanupWriteClaims()"

    def claim_control_directory_cleanup_write(self, request):
        if type(request) is not ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup:
            raise ManifestHandoffRegistryUnavailable
        prepared = request.prepared
        values = {
            "attempt": _encode(prepared.attempt_id),
            "directory": _encode(prepared.directory_id),
        }

        def action(connection):
            attempt = self._one(connection, _ATTEMPT, values, True)
            claim = self._one(connection, _CLAIM, values, True)
            if attempt is None:
                return None if claim is None else self._corrupt()
            if claim is not None:
                return self._retry(attempt, claim, prepared)
            clearance = self._one(connection, _CLEARANCE, values, True)
            if clearance is None:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if not self._base_binding(attempt, clearance, prepared):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            actor = UserId(_decode(attempt.actor_user_id))
            cleanup = CleanupManifestHandoffSupervisorControlDirectory(
                prepared.attempt_id, actor, prepared.directory_id
            )
            facts = self._clearances._facts(
                connection, cleanup, {**values, "actor": _encode(actor)}
            )
            if facts is None:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            retired, scope, journal, decision, management, hold, recovery, references = facts
            if not all((
                clearance.actor_user_id == _encode(actor),
                clearance.scope_id == _encode(scope),
                clearance.terminal_observation_id == _encode(journal.terminal_observation_id),
                clearance.decision_id == _encode(decision.decision_id),
                clearance.management_revision_id == _encode(management.revision_id),
                clearance.hold_revision_id == _encode(hold.revision_id),
                clearance.recovery_revision_id == _encode(recovery.revision_id),
                clearance.reference_revision_id == _encode(references.revision_id),
                retired.directory_id == prepared.directory_id,
            )):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            now = _utc(self._clock())
            if prepared.prepared_at < max(_utc(attempt.started_at), _utc(clearance.cleared_at)):
                raise ManifestHandoffRegistryUnavailable
            if now < prepared.prepared_at:
                raise ManifestHandoffRegistryUnavailable
            claim_id = self._new_claim_id()
            parameters = {
                **values,
                "claim": claim_id,
                "clearance": _encode(prepared.clearance_id),
                "preflight": _encode(prepared.preflight_id),
                "prepared": prepared.prepared_at,
                "claimed": now,
            }
            connection.execute(text(
                "INSERT INTO manifest_handoff_supervisor_control_cleanup_write_claims"
                " (claim_id,attempt_id,directory_id,clearance_id,preflight_id,prepared_at,claimed_at)"
                " VALUES (:claim,:attempt,:directory,:clearance,:preflight,:prepared,:claimed)"
            ), parameters)
            changed = connection.execute(text(
                "UPDATE manifest_handoff_supervisor_control_cleanup_attempts"
                " SET state='write_claimed',write_claimed_at=:claimed"
                " WHERE attempt_id=:attempt AND directory_id=:directory AND state='started'"
                " AND write_claimed_at IS NULL"
            ), parameters)
            if changed.rowcount != 1:
                raise ManifestHandoffRegistryUnavailable
            return ClaimedManifestHandoffSupervisorControlDirectoryCleanup(
                ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId(_decode(claim_id)),
                prepared,
                now,
            )

        return self._write(action)

    def resolve_control_directory_cleanup_write_claim(self, attempt_id):
        if type(attempt_id) is not ManifestHandoffSupervisorControlDirectoryCleanupAttemptId:
            raise ManifestHandoffRegistryUnavailable

        def action(connection):
            row = self._one(
                connection, _CLAIM_VIEW, {"attempt": _encode(attempt_id)}, True
            )
            if row is None:
                return None
            if row.state not in ("write_claimed", "outcome_unknown", "completed", "reconciled"):
                raise ManifestHandoffRegistryUnavailable
            if row.state == "completed" and row.outcome != "removed":
                raise ManifestHandoffRegistryUnavailable
            prepared_at = _utc(row.prepared_at)
            claimed_at = _utc(row.claimed_at)
            if (
                row.write_claimed_at is None
                or _utc(row.write_claimed_at) != claimed_at
                or prepared_at < _utc(row.started_at)
                or claimed_at < prepared_at
            ):
                raise ManifestHandoffRegistryUnavailable
            prepared = PreparedManifestHandoffSupervisorControlDirectoryCleanup(
                ManifestHandoffSupervisorControlDirectoryCleanupPreflightId(
                    _decode(row.preflight_id)),
                attempt_id,
                ManifestHandoffSupervisorControlDirectoryId(_decode(row.directory_id)),
                ManifestHandoffSupervisorControlDirectoryCleanupClearanceId(
                    _decode(row.clearance_id)),
                prepared_at,
            )
            return ClaimedManifestHandoffSupervisorControlDirectoryCleanup(
                ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId(
                    _decode(row.claim_id)),
                prepared,
                claimed_at,
            )

        return self._read(action)

    @staticmethod
    def _base_binding(attempt, clearance, prepared) -> bool:
        return all((
            attempt.state == "started",
            attempt.directory_id == _encode(prepared.directory_id),
            attempt.write_claimed_at is None,
            clearance.attempt_id == _encode(prepared.attempt_id),
            clearance.directory_id == _encode(prepared.directory_id),
            clearance.clearance_id == _encode(prepared.clearance_id),
        ))

    @staticmethod
    def _retry(attempt, row, prepared):
        if not all((
            attempt.state == "write_claimed",
            attempt.directory_id == _encode(prepared.directory_id),
            attempt.write_claimed_at is not None,
            row.directory_id == _encode(prepared.directory_id),
            row.clearance_id == _encode(prepared.clearance_id),
            row.preflight_id == _encode(prepared.preflight_id),
            _utc(row.prepared_at) == prepared.prepared_at,
            _utc(row.claimed_at) == _utc(attempt.write_claimed_at),
        )):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        return ClaimedManifestHandoffSupervisorControlDirectoryCleanup(
            ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId(_decode(row.claim_id)),
            prepared,
            _utc(row.claimed_at),
        )

    def _new_claim_id(self) -> bytes:
        try:
            return _encode(ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId(self._claim()))
        except (TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _one(connection, query, values, neutral=False):
        rows = connection.execute(query, values).all()
        if not rows:
            if neutral:
                return None
            raise ManifestHandoffRegistryUnavailable
        if len(rows) != 1:
            raise ManifestHandoffRegistryUnavailable
        return rows[0]

    @staticmethod
    def _corrupt():
        raise ManifestHandoffRegistryUnavailable

    def _write(self, action):
        try:
            with self._engine.begin() as connection:
                if connection.dialect.name == "postgresql":
                    connection.execute(text(
                        "LOCK TABLE identity_users,manifest_handoff_registry_scopes,"
                        " manifest_handoff_supervisor_control_directories,manifest_handoff_supervisor_journal_jobs,"
                        " manifest_handoff_supervisor_journal_transitions,manifest_handoff_supervisor_control_cleanup_decisions,"
                        " manifest_handoff_supervisor_cleanup_management_revisions,manifest_handoff_supervisor_cleanup_hold_revisions,"
                        " manifest_handoff_supervisor_cleanup_recovery_revisions,manifest_handoff_supervisor_cleanup_reference_revisions,"
                        " manifest_handoff_supervisor_control_cleanup_attempts,manifest_handoff_supervisor_cleanup_clearances,"
                        " manifest_handoff_supervisor_control_cleanup_write_claims IN SHARE ROW EXCLUSIVE MODE"
                    ))
                elif connection.dialect.name != "sqlite":
                    raise ManifestHandoffRegistryUnavailable
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable

    def _read(self, action):
        try:
            with self._engine.connect() as connection:
                if connection.dialect.name not in ("postgresql", "sqlite"):
                    raise ManifestHandoffRegistryUnavailable
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable
