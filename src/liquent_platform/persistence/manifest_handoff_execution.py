"""Atomic persistence for manifest-handoff execution ownership facts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    ClaimedManifestHandoffExecution,
    ManifestHandoffAttemptId,
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionEndId,
    ManifestHandoffExecutionEndKind,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffLeaseRenewalId,
    ManifestHandoffObservationId,
    ManifestHandoffOwnershipConflict,
    RecordedManifestHandoffExecutionEnd,
    RenewedManifestHandoffExecutionLease,
    StartedManifestHandoffExecution,
)
from liquent_platform.persistence.identity_errors import (
    ManifestHandoffRegistryUnavailable,
)


_LOCK = text(
    "LOCK TABLE identity_users,manifest_handoff_registry_scopes,"
    " manifest_handoff_registry_authorities,manifest_handoff_attempts,"
    " manifest_handoff_attempt_observations,manifest_handoff_execution_claims,"
    " manifest_handoff_execution_lease_renewals,manifest_handoff_execution_starts,"
    " manifest_handoff_execution_ends IN SHARE ROW EXCLUSIVE MODE"
)
_CURRENT_AUTHORITY = text(
    "SELECT 1 FROM identity_users user_fact"
    " JOIN manifest_handoff_registry_authorities authority"
    " ON authority.user_id=user_fact.user_id AND authority.scope_id=:scope"
    " JOIN manifest_handoff_registry_scopes scope"
    " ON scope.scope_id=authority.scope_id"
    " WHERE user_fact.user_id=:actor AND user_fact.status='active'"
    " AND scope.status='active' AND authority.status='active'"
)
_ATTEMPT = text(
    "SELECT attempt.attempt_id,attempt.scope_id,attempt.actor_user_id,"
    " observation.sequence_number,observation.kind"
    " FROM manifest_handoff_attempts attempt"
    " LEFT JOIN manifest_handoff_attempt_observations observation"
    " ON observation.attempt_id=attempt.attempt_id"
    " WHERE attempt.attempt_id=:attempt ORDER BY observation.sequence_number"
)
_CLAIM_BY_ID = text(
    "SELECT claim_id,attempt_id,actor_user_id,owner_id,claimed_at,lease_expires_at"
    " FROM manifest_handoff_execution_claims WHERE claim_id=:claim"
)
_CLAIM_BY_ATTEMPT = text(
    "SELECT claim_id FROM manifest_handoff_execution_claims WHERE attempt_id=:attempt"
)
_CLAIM_STATE = text(
    "SELECT claim.claim_id,claim.attempt_id,claim.actor_user_id,claim.owner_id,"
    " attempt.scope_id,start.observation_id,start.started_at,end_fact.end_id"
    " FROM manifest_handoff_execution_claims claim"
    " JOIN manifest_handoff_attempts attempt ON attempt.attempt_id=claim.attempt_id"
    " LEFT JOIN manifest_handoff_execution_starts start ON start.claim_id=claim.claim_id"
    " LEFT JOIN manifest_handoff_execution_ends end_fact ON end_fact.claim_id=claim.claim_id"
    " WHERE claim.claim_id=:claim"
)
_HISTORY = text(
    "SELECT observation_id,sequence_number,kind FROM manifest_handoff_attempt_observations"
    " WHERE attempt_id=:attempt ORDER BY sequence_number"
)
_RENEWAL = text(
    "SELECT renewal_id,claim_id,owner_id,renewed_at,lease_expires_at"
    " FROM manifest_handoff_execution_lease_renewals WHERE renewal_id=:renewal"
)
_START_BY_OBSERVATION = text(
    "SELECT start.claim_id,start.observation_id,start.owner_id,start.started_at,"
    " claim.attempt_id,observation.attempt_id AS observation_attempt_id,"
    " observation.kind AS observation_kind"
    " FROM manifest_handoff_execution_starts start"
    " JOIN manifest_handoff_execution_claims claim ON claim.claim_id=start.claim_id"
    " JOIN manifest_handoff_attempt_observations observation"
    " ON observation.observation_id=start.observation_id"
    " WHERE start.observation_id=:observation"
)
_OBSERVATION = text(
    "SELECT observation_id FROM manifest_handoff_attempt_observations"
    " WHERE observation_id=:observation"
)
_END_BY_ID = text(
    "SELECT end_fact.end_id,end_fact.claim_id,end_fact.owner_id,end_fact.kind,"
    " end_fact.ended_at,claim.attempt_id"
    " FROM manifest_handoff_execution_ends end_fact"
    " JOIN manifest_handoff_execution_claims claim ON claim.claim_id=end_fact.claim_id"
    " WHERE end_fact.end_id=:end"
)
_END_BY_CLAIM = text(
    "SELECT end_id FROM manifest_handoff_execution_ends WHERE claim_id=:claim"
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


class DatabaseManifestHandoffExecutionOwnership:
    """Persist one non-transferable execution owner and its direct facts."""

    __slots__ = ("_engine", "_lease_duration", "_clock")

    def __init__(
        self,
        engine: Engine,
        *,
        lease_duration: timedelta,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if type(lease_duration) is not timedelta or lease_duration <= timedelta(0):
            raise ValueError("manifest handoff execution lease duration must be positive")
        self._engine = engine
        self._lease_duration = lease_duration
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffExecutionOwnership()"

    def claim_execution(self, claim_id, attempt_id, actor_user_id, owner_id):
        if not all((
            type(claim_id) is ManifestHandoffExecutionClaimId,
            type(attempt_id) is ManifestHandoffAttemptId,
            type(actor_user_id) is str and bool(actor_user_id),
            type(owner_id) is ManifestHandoffExecutionOwnerId,
        )):
            raise ManifestHandoffRegistryUnavailable
        values = {
            "claim": _encode(claim_id), "attempt": _encode(attempt_id),
            "actor": _encode(actor_user_id), "owner": _encode(owner_id),
        }
        return self._public(self._claim, values, claim_id, attempt_id, actor_user_id, owner_id)

    def _claim(self, transaction, values, claim_id, attempt_id, actor_user_id, owner_id):
        rows = transaction.execute(_CLAIM_BY_ID, values).all()
        if rows:
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            if (
                row.attempt_id != values["attempt"]
                or row.actor_user_id != values["actor"]
                or row.owner_id != values["owner"]
            ):
                return ManifestHandoffOwnershipConflict()
            return ClaimedManifestHandoffExecution(
                claim_id, attempt_id, owner_id,
                _utc(row.claimed_at), _utc(row.lease_expires_at),
            )
        attempts = transaction.execute(_ATTEMPT, values).all()
        if not attempts:
            return None
        if (
            len(attempts) != 1
            or attempts[0].sequence_number != 1
            or attempts[0].kind != "reserved"
        ):
            return None
        attempt = attempts[0]
        if attempt.actor_user_id != values["actor"]:
            return None
        if transaction.execute(_CLAIM_BY_ATTEMPT, values).first() is not None:
            return ManifestHandoffOwnershipConflict()
        if transaction.execute(
            _CURRENT_AUTHORITY,
            {"actor": values["actor"], "scope": attempt.scope_id},
        ).first() is None:
            return None
        now = _utc(self._clock())
        try:
            expires = now + self._lease_duration
        except OverflowError:
            raise ManifestHandoffRegistryUnavailable from None
        values.update(now=now, expires=expires)
        transaction.execute(text(
            "INSERT INTO manifest_handoff_execution_claims"
            " (claim_id,attempt_id,actor_user_id,owner_id,claimed_at,lease_expires_at)"
            " VALUES (:claim,:attempt,:actor,:owner,:now,:expires)"
        ), values)
        return ClaimedManifestHandoffExecution(
            claim_id, attempt_id, owner_id, now, expires
        )

    def renew_execution_lease(self, renewal_id, claim_id, owner_id):
        if not all((
            type(renewal_id) is ManifestHandoffLeaseRenewalId,
            type(claim_id) is ManifestHandoffExecutionClaimId,
            type(owner_id) is ManifestHandoffExecutionOwnerId,
        )):
            raise ManifestHandoffRegistryUnavailable
        values = {
            "renewal": _encode(renewal_id), "claim": _encode(claim_id),
            "owner": _encode(owner_id),
        }
        return self._public(self._renew, values, renewal_id, claim_id, owner_id)

    def _renew(self, transaction, values, renewal_id, claim_id, owner_id):
        rows = transaction.execute(_RENEWAL, values).all()
        if rows:
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            if row.claim_id != values["claim"] or row.owner_id != values["owner"]:
                return ManifestHandoffOwnershipConflict()
            return RenewedManifestHandoffExecutionLease(
                renewal_id, claim_id, owner_id,
                _utc(row.renewed_at), _utc(row.lease_expires_at),
            )
        claims = transaction.execute(_CLAIM_STATE, values).all()
        if not claims:
            return None
        if len(claims) != 1:
            raise ManifestHandoffRegistryUnavailable
        claim = claims[0]
        if claim.owner_id != values["owner"] or claim.end_id is not None:
            return None
        now = _utc(self._clock())
        expires = now + self._lease_duration
        values.update(now=now, expires=expires)
        transaction.execute(text(
            "INSERT INTO manifest_handoff_execution_lease_renewals"
            " (renewal_id,claim_id,owner_id,renewed_at,lease_expires_at)"
            " VALUES (:renewal,:claim,:owner,:now,:expires)"
        ), values)
        return RenewedManifestHandoffExecutionLease(
            renewal_id, claim_id, owner_id, now, expires
        )

    def start_claimed_execution(self, observation_id, claim_id, owner_id):
        if not all((
            type(observation_id) is ManifestHandoffObservationId,
            type(claim_id) is ManifestHandoffExecutionClaimId,
            type(owner_id) is ManifestHandoffExecutionOwnerId,
        )):
            raise ManifestHandoffRegistryUnavailable
        values = {
            "observation": _encode(observation_id), "claim": _encode(claim_id),
            "owner": _encode(owner_id),
        }
        return self._public(self._start, values, observation_id, claim_id, owner_id)

    def _start(self, transaction, values, observation_id, claim_id, owner_id):
        rows = transaction.execute(_START_BY_OBSERVATION, values).all()
        if rows:
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            if row.claim_id != values["claim"] or row.owner_id != values["owner"]:
                return ManifestHandoffOwnershipConflict()
            return StartedManifestHandoffExecution(
                claim_id, ManifestHandoffAttemptId(_decode(row.attempt_id)),
                observation_id, owner_id, _utc(row.started_at),
            )
        claims = transaction.execute(_CLAIM_STATE, values).all()
        if not claims:
            return None
        if len(claims) != 1:
            raise ManifestHandoffRegistryUnavailable
        claim = claims[0]
        if claim.owner_id != values["owner"] or claim.end_id is not None:
            return None
        if claim.observation_id is not None:
            return ManifestHandoffOwnershipConflict()
        if transaction.execute(_OBSERVATION, values).first() is not None:
            return ManifestHandoffOwnershipConflict()
        if transaction.execute(
            _CURRENT_AUTHORITY,
            {"actor": claim.actor_user_id, "scope": claim.scope_id},
        ).first() is None:
            return None
        values["attempt"] = claim.attempt_id
        history = transaction.execute(_HISTORY, values).all()
        if len(history) != 1 or history[0].sequence_number != 1 or history[0].kind != "reserved":
            return None
        now = _utc(self._clock())
        values["now"] = now
        transaction.execute(text(
            "INSERT INTO manifest_handoff_attempt_observations"
            " (observation_id,attempt_id,sequence_number,kind,manifest_sha256,"
            " file_count,observed_at)"
            " VALUES (:observation,:attempt,2,'writer_started',NULL,NULL,:now)"
        ), values)
        transaction.execute(text(
            "INSERT INTO manifest_handoff_execution_starts"
            " (claim_id,observation_id,owner_id,started_at)"
            " VALUES (:claim,:observation,:owner,:now)"
        ), values)
        return StartedManifestHandoffExecution(
            claim_id, ManifestHandoffAttemptId(_decode(claim.attempt_id)),
            observation_id, owner_id, now,
        )

    def record_outcome_secured(self, end_id, claim_id, owner_id):
        return self._end_public(
            end_id, claim_id, owner_id, ManifestHandoffExecutionEndKind.OUTCOME_SECURED
        )

    def record_outcome_unknown(self, end_id, claim_id, owner_id):
        return self._end_public(
            end_id, claim_id, owner_id, ManifestHandoffExecutionEndKind.OUTCOME_UNKNOWN
        )

    def record_start_not_confirmed(self, end_id, claim_id, owner_id):
        return self._end_public(
            end_id, claim_id, owner_id,
            ManifestHandoffExecutionEndKind.START_NOT_CONFIRMED,
        )

    def _end_public(self, end_id, claim_id, owner_id, kind):
        if not all((
            type(end_id) is ManifestHandoffExecutionEndId,
            type(claim_id) is ManifestHandoffExecutionClaimId,
            type(owner_id) is ManifestHandoffExecutionOwnerId,
            type(kind) is ManifestHandoffExecutionEndKind,
        )):
            raise ManifestHandoffRegistryUnavailable
        values = {
            "end": _encode(end_id), "claim": _encode(claim_id),
            "owner": _encode(owner_id), "kind": kind.value,
        }
        return self._public(self._end, values, end_id, claim_id, owner_id, kind)

    def _end(self, transaction, values, end_id, claim_id, owner_id, kind):
        rows = transaction.execute(_END_BY_ID, values).all()
        if rows:
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            if (
                row.claim_id != values["claim"]
                or row.owner_id != values["owner"]
                or row.kind != values["kind"]
            ):
                return ManifestHandoffOwnershipConflict()
            return RecordedManifestHandoffExecutionEnd(
                end_id, claim_id, ManifestHandoffAttemptId(_decode(row.attempt_id)),
                kind, _utc(row.ended_at),
            )
        claims = transaction.execute(_CLAIM_STATE, values).all()
        if not claims:
            return None
        if len(claims) != 1:
            raise ManifestHandoffRegistryUnavailable
        claim = claims[0]
        if claim.owner_id != values["owner"]:
            return None
        if claim.end_id is not None or transaction.execute(_END_BY_CLAIM, values).first():
            return ManifestHandoffOwnershipConflict()
        values["attempt"] = claim.attempt_id
        history = transaction.execute(_HISTORY, values).all()
        started = claim.observation_id is not None
        self._validate_history(history, claim.observation_id)
        if kind is ManifestHandoffExecutionEndKind.START_NOT_CONFIRMED:
            if started:
                return None
        elif not started:
            return None
        elif kind is ManifestHandoffExecutionEndKind.OUTCOME_SECURED and (
            len(history) < 3 or history[-1].kind == "writer_started"
        ):
            return None
        now = _utc(self._clock())
        values["now"] = now
        transaction.execute(text(
            "INSERT INTO manifest_handoff_execution_ends"
            " (end_id,claim_id,owner_id,kind,ended_at)"
            " VALUES (:end,:claim,:owner,:kind,:now)"
        ), values)
        return RecordedManifestHandoffExecutionEnd(
            end_id, claim_id, ManifestHandoffAttemptId(_decode(claim.attempt_id)),
            kind, now,
        )

    @staticmethod
    def _validate_history(history, start_observation) -> None:
        if not history:
            raise ManifestHandoffRegistryUnavailable
        for expected, row in enumerate(history, 1):
            if row.sequence_number != expected:
                raise ManifestHandoffRegistryUnavailable
        if history[0].kind != "reserved":
            raise ManifestHandoffRegistryUnavailable
        if start_observation is None:
            if len(history) != 1:
                raise ManifestHandoffRegistryUnavailable
            return
        if (
            len(history) < 2
            or history[1].kind != "writer_started"
            or history[1].observation_id != start_observation
        ):
            raise ManifestHandoffRegistryUnavailable
        previous = "writer_started"
        reconciliations = {
            "manifest_absent", "manifest_temporary_only", "manifest_handed_off",
            "manifest_handed_off_pending_cleanup", "manifest_handoff_conflict",
        }
        for row in history[2:]:
            kind = row.kind
            allowed = (
                (previous == "writer_started" and kind in {
                    "writer_handed_off", "writer_outcome_unknown"
                })
                or kind in reconciliations
                or (
                    previous == "manifest_handed_off_pending_cleanup"
                    and kind in {"cleanup_completed", "cleanup_outcome_unknown"}
                )
            )
            if not allowed:
                raise ManifestHandoffRegistryUnavailable
            previous = kind

    def _public(self, operation, values, *arguments):
        try:
            with self._engine.begin() as transaction:
                if transaction.dialect.name == "postgresql":
                    transaction.execute(_LOCK)
                elif transaction.dialect.name != "sqlite":
                    raise ManifestHandoffRegistryUnavailable
                return operation(transaction, values, *arguments)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable
