"""Atomic persistent recovery claims and reconciliation observations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff import (
    AppendedManifestHandoffObservation,
    AppendedManifestHandoffRecoveryObservation,
    ClaimedManifestHandoffRecovery,
    ManifestHandoffAttemptId,
    ManifestHandoffExecutionClaimId,
    ManifestHandoffFacts,
    ManifestHandoffObservationId,
    ManifestHandoffObservationKind,
    ManifestHandoffOwnershipConflict,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryEndId,
    ManifestHandoffRecoveryEndKind,
    ManifestHandoffRecoveryOwnerId,
    ManifestHandoffRecoveryRequest,
    RecordedManifestHandoffRecoveryEnd,
)
from liquent_platform.persistence.identity_errors import (
    ManifestHandoffRegistryUnavailable,
)


_LOCK = text(
    "LOCK TABLE identity_users,manifest_handoff_registry_scopes,"
    " manifest_handoff_recovery_authorities,manifest_handoff_attempts,"
    " manifest_handoff_attempt_observations,manifest_handoff_execution_claims,"
    " manifest_handoff_execution_ends,manifest_handoff_recovery_claims,"
    " manifest_handoff_recovery_ends,manifest_handoff_recovery_observations"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_CURRENT_AUTHORITY = text(
    "SELECT 1 FROM identity_users user_fact"
    " JOIN manifest_handoff_recovery_authorities authority"
    " ON authority.user_id=user_fact.user_id AND authority.scope_id=:scope"
    " JOIN manifest_handoff_registry_scopes scope"
    " ON scope.scope_id=authority.scope_id"
    " WHERE user_fact.user_id=:actor AND user_fact.status='active'"
    " AND scope.status='active' AND authority.status='active'"
)
_CLAIM_BY_ID = text(
    "SELECT recovery.claim_id,recovery.attempt_id,recovery.execution_end_id,"
    " recovery.actor_user_id,recovery.owner_id,recovery.claimed_at,recovery.ended_at,"
    " attempt.scope_id,attempt.handoff_name,execution.claim_id AS execution_claim_id"
    " FROM manifest_handoff_recovery_claims recovery"
    " JOIN manifest_handoff_attempts attempt ON attempt.attempt_id=recovery.attempt_id"
    " JOIN manifest_handoff_execution_ends execution_end"
    " ON execution_end.end_id=recovery.execution_end_id"
    " JOIN manifest_handoff_execution_claims execution"
    " ON execution.claim_id=execution_end.claim_id"
    " WHERE recovery.claim_id=:claim"
)
_ATTEMPT_END = text(
    "SELECT attempt.attempt_id,attempt.scope_id,attempt.handoff_name,"
    " execution.claim_id AS execution_claim_id,execution_end.end_id AS execution_end_id"
    " FROM manifest_handoff_attempts attempt"
    " JOIN manifest_handoff_execution_claims execution"
    " ON execution.attempt_id=attempt.attempt_id"
    " JOIN manifest_handoff_execution_ends execution_end"
    " ON execution_end.claim_id=execution.claim_id"
    " WHERE attempt.scope_id=:scope AND attempt.handoff_name=:name"
)
_PRIOR_CLAIMS = text(
    "SELECT recovery.claim_id,recovery.ended_at,recovery_end.end_id,"
    " recovery_end.ended_at AS end_ended_at"
    " FROM manifest_handoff_recovery_claims recovery"
    " LEFT JOIN manifest_handoff_recovery_ends recovery_end"
    " ON recovery_end.claim_id=recovery.claim_id"
    " WHERE recovery.attempt_id=:attempt"
)
_CLAIM_STATE = text(
    "SELECT recovery.claim_id,recovery.attempt_id,recovery.owner_id,"
    " recovery.claimed_at,recovery.ended_at,execution.claim_id AS execution_claim_id,"
    " recovery_observation.observation_id,recovery_end.end_id"
    " FROM manifest_handoff_recovery_claims recovery"
    " JOIN manifest_handoff_execution_ends execution_end"
    " ON execution_end.end_id=recovery.execution_end_id"
    " JOIN manifest_handoff_execution_claims execution"
    " ON execution.claim_id=execution_end.claim_id"
    " LEFT JOIN manifest_handoff_recovery_observations recovery_observation"
    " ON recovery_observation.claim_id=recovery.claim_id"
    " LEFT JOIN manifest_handoff_recovery_ends recovery_end"
    " ON recovery_end.claim_id=recovery.claim_id"
    " WHERE recovery.claim_id=:claim"
)
_HISTORY = text(
    "SELECT observation_id,sequence_number,kind,manifest_sha256,file_count,observed_at"
    " FROM manifest_handoff_attempt_observations"
    " WHERE attempt_id=:attempt ORDER BY sequence_number"
)
_OBSERVATION = text(
    "SELECT observation.observation_id,observation.attempt_id,"
    " observation.sequence_number,observation.kind,observation.manifest_sha256,"
    " observation.file_count,observation.observed_at,recovery.claim_id,"
    " recovery_claim.owner_id"
    " FROM manifest_handoff_attempt_observations observation"
    " LEFT JOIN manifest_handoff_recovery_observations recovery"
    " ON recovery.observation_id=observation.observation_id"
    " LEFT JOIN manifest_handoff_recovery_claims recovery_claim"
    " ON recovery_claim.claim_id=recovery.claim_id"
    " WHERE observation.observation_id=:observation"
)
_END_BY_ID = text(
    "SELECT recovery_end.end_id,recovery_end.claim_id,recovery_end.owner_id,"
    " recovery_end.kind,recovery_end.ended_at,recovery.attempt_id,recovery.ended_at"
    " AS claim_ended_at FROM manifest_handoff_recovery_ends recovery_end"
    " JOIN manifest_handoff_recovery_claims recovery"
    " ON recovery.claim_id=recovery_end.claim_id WHERE recovery_end.end_id=:end"
)
_END_BY_CLAIM = text(
    "SELECT end_id FROM manifest_handoff_recovery_ends WHERE claim_id=:claim"
)

_FACTUAL = {
    ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY,
    ManifestHandoffObservationKind.MANIFEST_HANDED_OFF,
    ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
}
_RECONCILIATIONS = {
    ManifestHandoffObservationKind.MANIFEST_ABSENT,
    *_FACTUAL,
    ManifestHandoffObservationKind.MANIFEST_HANDOFF_CONFLICT,
}


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


def _facts(digest: object, count: object) -> ManifestHandoffFacts | None:
    if digest is None and count is None:
        return None
    try:
        return ManifestHandoffFacts(digest, count)
    except (TypeError, ValueError):
        raise ManifestHandoffRegistryUnavailable from None


class DatabaseManifestHandoffRecovery:
    """Persist authorized read-only recovery ownership and direct outcomes."""

    __slots__ = ("_engine", "_clock")

    def __init__(
        self, engine: Engine, *, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffRecovery()"

    def claim_recovery(self, request):
        if type(request) is not ManifestHandoffRecoveryRequest:
            raise ManifestHandoffRegistryUnavailable
        values = {
            "claim": _encode(request.claim_id),
            "actor": _encode(request.actor_user_id),
            "scope": _encode(request.scope_id),
            "name": request.handoff_name.value,
            "owner": _encode(request.owner_id),
        }
        return self._public(self._claim, values, request)

    def _claim(self, transaction, values, request):
        rows = transaction.execute(_CLAIM_BY_ID, values).all()
        if rows:
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            if (
                row.actor_user_id != values["actor"]
                or row.scope_id != values["scope"]
                or row.handoff_name != values["name"]
                or row.owner_id != values["owner"]
            ):
                return ManifestHandoffOwnershipConflict()
            return ClaimedManifestHandoffRecovery(
                request.claim_id,
                ManifestHandoffAttemptId(_decode(row.attempt_id)),
                ManifestHandoffExecutionClaimId(_decode(row.execution_claim_id)),
                request.owner_id,
                _utc(row.claimed_at),
            )
        attempts = transaction.execute(_ATTEMPT_END, values).all()
        if not attempts:
            return None
        if len(attempts) != 1:
            raise ManifestHandoffRegistryUnavailable
        attempt = attempts[0]
        values.update(
            attempt=attempt.attempt_id, execution_end=attempt.execution_end_id
        )
        history = transaction.execute(_HISTORY, values).all()
        self._validate_history(history)
        if self._is_resolved(history[-1].kind):
            return None
        if transaction.execute(_CURRENT_AUTHORITY, values).first() is None:
            return None
        prior_claims = transaction.execute(_PRIOR_CLAIMS, values).all()
        active = False
        for prior in prior_claims:
            if (prior.ended_at is None) != (prior.end_id is None):
                raise ManifestHandoffRegistryUnavailable
            if prior.ended_at is not None and (
                prior.end_ended_at is None
                or _utc(prior.ended_at) != _utc(prior.end_ended_at)
            ):
                raise ManifestHandoffRegistryUnavailable
            active = active or prior.ended_at is None
        if active:
            return None
        now = _utc(self._clock())
        values["now"] = now
        transaction.execute(text(
            "INSERT INTO manifest_handoff_recovery_claims"
            " (claim_id,attempt_id,execution_end_id,actor_user_id,owner_id,"
            " claimed_at,ended_at)"
            " VALUES (:claim,:attempt,:execution_end,:actor,:owner,:now,NULL)"
        ), values)
        return ClaimedManifestHandoffRecovery(
            request.claim_id,
            ManifestHandoffAttemptId(_decode(attempt.attempt_id)),
            ManifestHandoffExecutionClaimId(_decode(attempt.execution_claim_id)),
            request.owner_id,
            now,
        )

    def record_manifest_absent(self, observation_id, claim_id, owner_id):
        return self._append_public(
            observation_id, claim_id, owner_id,
            ManifestHandoffObservationKind.MANIFEST_ABSENT, None,
        )

    def record_manifest_temporary_only(
        self, observation_id, claim_id, owner_id, facts
    ):
        return self._append_public(
            observation_id, claim_id, owner_id,
            ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY, facts,
        )

    def record_manifest_handed_off(
        self, observation_id, claim_id, owner_id, facts
    ):
        return self._append_public(
            observation_id, claim_id, owner_id,
            ManifestHandoffObservationKind.MANIFEST_HANDED_OFF, facts,
        )

    def record_manifest_handed_off_pending_cleanup(
        self, observation_id, claim_id, owner_id, facts
    ):
        return self._append_public(
            observation_id, claim_id, owner_id,
            ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
            facts,
        )

    def record_manifest_handoff_conflict(self, observation_id, claim_id, owner_id):
        return self._append_public(
            observation_id, claim_id, owner_id,
            ManifestHandoffObservationKind.MANIFEST_HANDOFF_CONFLICT, None,
        )

    def _append_public(self, observation_id, claim_id, owner_id, kind, facts):
        if (
            type(observation_id) is not ManifestHandoffObservationId
            or type(claim_id) is not ManifestHandoffRecoveryClaimId
            or type(owner_id) is not ManifestHandoffRecoveryOwnerId
            or type(kind) is not ManifestHandoffObservationKind
            or (kind in _FACTUAL) != (type(facts) is ManifestHandoffFacts)
        ):
            raise ManifestHandoffRegistryUnavailable
        values = {
            "observation": _encode(observation_id), "claim": _encode(claim_id),
            "owner": _encode(owner_id), "kind": kind.value,
            "digest": facts.manifest_sha256 if facts else None,
            "count": facts.file_count if facts else None,
        }
        return self._public(
            self._append, values, observation_id, claim_id, owner_id, kind, facts
        )

    def _append(
        self, transaction, values, observation_id, claim_id, owner_id, kind, facts
    ):
        rows = transaction.execute(_OBSERVATION, values).all()
        if rows:
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            stored_facts = _facts(row.manifest_sha256, row.file_count)
            if (
                row.claim_id != values["claim"]
                or row.owner_id != values["owner"]
                or row.kind != values["kind"]
                or stored_facts != facts
            ):
                return ManifestHandoffOwnershipConflict()
            observation = AppendedManifestHandoffObservation(
                observation_id,
                ManifestHandoffAttemptId(_decode(row.attempt_id)),
                row.sequence_number,
                ManifestHandoffObservationKind(row.kind),
                _utc(row.observed_at),
                stored_facts,
            )
            return AppendedManifestHandoffRecoveryObservation(claim_id, observation)
        claims = transaction.execute(_CLAIM_STATE, values).all()
        if not claims:
            return None
        if len(claims) != 1:
            raise ManifestHandoffRegistryUnavailable
        claim = claims[0]
        if (
            claim.owner_id != values["owner"]
            or claim.ended_at is not None
            or claim.end_id is not None
        ):
            return None
        if claim.observation_id is not None:
            return ManifestHandoffOwnershipConflict()
        values["attempt"] = claim.attempt_id
        history = transaction.execute(_HISTORY, values).all()
        self._validate_history(history)
        sequence = len(history) + 1
        now = _utc(self._clock())
        values.update(sequence=sequence, now=now)
        transaction.execute(text(
            "INSERT INTO manifest_handoff_attempt_observations"
            " (observation_id,attempt_id,sequence_number,kind,manifest_sha256,"
            " file_count,observed_at)"
            " VALUES (:observation,:attempt,:sequence,:kind,:digest,:count,:now)"
        ), values)
        transaction.execute(text(
            "INSERT INTO manifest_handoff_recovery_observations"
            " (claim_id,observation_id) VALUES (:claim,:observation)"
        ), values)
        observation = AppendedManifestHandoffObservation(
            observation_id,
            ManifestHandoffAttemptId(_decode(claim.attempt_id)),
            sequence,
            kind,
            now,
            facts,
        )
        return AppendedManifestHandoffRecoveryObservation(claim_id, observation)

    def record_outcome_secured(self, end_id, claim_id, owner_id):
        return self._end_public(
            end_id, claim_id, owner_id, ManifestHandoffRecoveryEndKind.OUTCOME_SECURED
        )

    def record_outcome_unknown(self, end_id, claim_id, owner_id):
        return self._end_public(
            end_id, claim_id, owner_id, ManifestHandoffRecoveryEndKind.OUTCOME_UNKNOWN
        )

    def record_start_not_confirmed(self, end_id, claim_id, owner_id):
        return self._end_public(
            end_id, claim_id, owner_id,
            ManifestHandoffRecoveryEndKind.START_NOT_CONFIRMED,
        )

    def _end_public(self, end_id, claim_id, owner_id, kind):
        if not all((
            type(end_id) is ManifestHandoffRecoveryEndId,
            type(claim_id) is ManifestHandoffRecoveryClaimId,
            type(owner_id) is ManifestHandoffRecoveryOwnerId,
            type(kind) is ManifestHandoffRecoveryEndKind,
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
            ended = _utc(row.ended_at)
            if _utc(row.claim_ended_at) != ended:
                raise ManifestHandoffRegistryUnavailable
            return RecordedManifestHandoffRecoveryEnd(
                end_id, claim_id, ManifestHandoffAttemptId(_decode(row.attempt_id)),
                kind, ended,
            )
        claims = transaction.execute(_CLAIM_STATE, values).all()
        if not claims:
            return None
        if len(claims) != 1:
            raise ManifestHandoffRegistryUnavailable
        claim = claims[0]
        if claim.owner_id != values["owner"]:
            return None
        if claim.ended_at is not None or claim.end_id is not None:
            return ManifestHandoffOwnershipConflict()
        observed = claim.observation_id is not None
        if kind is ManifestHandoffRecoveryEndKind.OUTCOME_SECURED and not observed:
            return None
        if kind is not ManifestHandoffRecoveryEndKind.OUTCOME_SECURED and observed:
            return None
        now = _utc(self._clock())
        values["now"] = now
        transaction.execute(text(
            "INSERT INTO manifest_handoff_recovery_ends"
            " (end_id,claim_id,owner_id,kind,ended_at)"
            " VALUES (:end,:claim,:owner,:kind,:now)"
        ), values)
        transaction.execute(text(
            "UPDATE manifest_handoff_recovery_claims SET ended_at=:now"
            " WHERE claim_id=:claim AND ended_at IS NULL"
        ), values)
        return RecordedManifestHandoffRecoveryEnd(
            end_id, claim_id, ManifestHandoffAttemptId(_decode(claim.attempt_id)),
            kind, now,
        )

    @staticmethod
    def _is_resolved(kind: str) -> bool:
        return kind in {
            "writer_handed_off", "manifest_absent", "manifest_temporary_only",
            "manifest_handed_off", "manifest_handed_off_pending_cleanup",
            "manifest_handoff_conflict", "cleanup_completed",
            "cleanup_outcome_unknown",
        }

    @staticmethod
    def _validate_history(history) -> None:
        if not history:
            raise ManifestHandoffRegistryUnavailable
        previous = None
        factual = {kind.value for kind in _FACTUAL} | {"writer_handed_off", "cleanup_completed"}
        reconciliations = {kind.value for kind in _RECONCILIATIONS}
        for expected, row in enumerate(history, 1):
            if row.sequence_number != expected:
                raise ManifestHandoffRegistryUnavailable
            kind = row.kind
            facts = _facts(row.manifest_sha256, row.file_count)
            _utc(row.observed_at)
            if (kind in factual) != (facts is not None):
                raise ManifestHandoffRegistryUnavailable
            if expected == 1:
                if kind != "reserved":
                    raise ManifestHandoffRegistryUnavailable
            elif expected == 2:
                if kind != "writer_started" and kind not in reconciliations:
                    raise ManifestHandoffRegistryUnavailable
            else:
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
