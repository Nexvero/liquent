"""Atomic append-only persistence for controlled manifest-handoff observations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.manifest_handoff import (
    AppendedManifestHandoffObservation,
    ManifestHandoffAttemptId,
    ManifestHandoffFacts,
    ManifestHandoffObservationConflict,
    ManifestHandoffObservationId,
    ManifestHandoffObservationKind,
)
from liquent_platform.persistence.identity_errors import (
    ManifestHandoffRegistryUnavailable,
)


_LOCK = text(
    "LOCK TABLE identity_users,manifest_handoff_registry_scopes,"
    " manifest_handoff_registry_authorities,manifest_handoff_attempts,"
    " manifest_handoff_attempt_observations IN SHARE ROW EXCLUSIVE MODE"
)
_EXISTING = text(
    "SELECT observation_id,attempt_id,sequence_number,kind,manifest_sha256,"
    " file_count,observed_at FROM manifest_handoff_attempt_observations"
    " WHERE observation_id=:observation"
)
_ATTEMPT = text(
    "SELECT attempt_id,scope_id,actor_user_id FROM manifest_handoff_attempts"
    " WHERE attempt_id=:attempt"
)
_HISTORY = text(
    "SELECT observation_id,sequence_number,kind,manifest_sha256,file_count,"
    " observed_at FROM manifest_handoff_attempt_observations"
    " WHERE attempt_id=:attempt ORDER BY sequence_number"
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

_FACTUAL = {
    ManifestHandoffObservationKind.WRITER_HANDED_OFF,
    ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY,
    ManifestHandoffObservationKind.MANIFEST_HANDED_OFF,
    ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
    ManifestHandoffObservationKind.CLEANUP_COMPLETED,
}
_RECONCILIATIONS = {
    ManifestHandoffObservationKind.MANIFEST_ABSENT,
    ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY,
    ManifestHandoffObservationKind.MANIFEST_HANDED_OFF,
    ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
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


class DatabaseManifestHandoffObservationAppend:
    """Implement all source-specific append ports with one private algorithm."""

    __slots__ = ("_engine", "_clock")

    def __init__(
        self, engine: Engine, *, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffObservationAppend()"

    def record_writer_started(self, observation_id, attempt_id):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.WRITER_STARTED, None, True,
        )

    def record_writer_handed_off(self, observation_id, attempt_id, facts):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.WRITER_HANDED_OFF, facts, False,
        )

    def record_writer_outcome_unknown(self, observation_id, attempt_id):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.WRITER_OUTCOME_UNKNOWN, None, False,
        )

    def record_manifest_absent(self, observation_id, attempt_id):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.MANIFEST_ABSENT, None, False,
        )

    def record_manifest_temporary_only(self, observation_id, attempt_id, facts):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.MANIFEST_TEMPORARY_ONLY, facts, False,
        )

    def record_manifest_handed_off(self, observation_id, attempt_id, facts):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.MANIFEST_HANDED_OFF, facts, False,
        )

    def record_manifest_handed_off_pending_cleanup(
        self, observation_id, attempt_id, facts
    ):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP,
            facts, False,
        )

    def record_manifest_handoff_conflict(self, observation_id, attempt_id):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.MANIFEST_HANDOFF_CONFLICT, None, False,
        )

    def record_cleanup_completed(self, observation_id, attempt_id, facts):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.CLEANUP_COMPLETED, facts, False,
        )

    def record_cleanup_outcome_unknown(self, observation_id, attempt_id):
        return self._public_append(
            observation_id, attempt_id,
            ManifestHandoffObservationKind.CLEANUP_OUTCOME_UNKNOWN, None, False,
        )

    def _public_append(
        self, observation_id, attempt_id, kind, facts, require_authority
    ):
        try:
            if (
                type(observation_id) is not ManifestHandoffObservationId
                or type(attempt_id) is not ManifestHandoffAttemptId
                or type(kind) is not ManifestHandoffObservationKind
                or type(require_authority) is not bool
                or ((kind in _FACTUAL) != (type(facts) is ManifestHandoffFacts))
            ):
                raise ManifestHandoffRegistryUnavailable
            values = {
                "observation": _encode(observation_id),
                "attempt": _encode(attempt_id),
                "kind": kind.value,
                "digest": facts.manifest_sha256 if facts else None,
                "count": facts.file_count if facts else None,
            }
            with self._engine.begin() as transaction:
                return self._append(
                    transaction, observation_id, attempt_id, kind, facts,
                    require_authority, values,
                )
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable

    def _append(
        self, transaction: Connection, observation_id, attempt_id, kind, facts,
        require_authority, values,
    ):
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise ManifestHandoffRegistryUnavailable

        existing = transaction.execute(_EXISTING, values).all()
        if existing:
            return self._retry(existing, observation_id, attempt_id, kind, facts, values)

        attempts = transaction.execute(_ATTEMPT, values).all()
        if not attempts:
            return None
        if len(attempts) != 1:
            raise ManifestHandoffRegistryUnavailable
        attempt = attempts[0]
        if require_authority and transaction.execute(
            _CURRENT_AUTHORITY,
            {"actor": attempt.actor_user_id, "scope": attempt.scope_id},
        ).first() is None:
            return None

        rows = transaction.execute(_HISTORY, values).all()
        latest = self._validate_history(rows)
        if not self._transition_allowed(latest, kind):
            return None
        sequence = len(rows) + 1
        now = _utc(self._clock())
        values.update(sequence=sequence, now=now)
        transaction.execute(text(
            "INSERT INTO manifest_handoff_attempt_observations"
            " (observation_id,attempt_id,sequence_number,kind,manifest_sha256,"
            " file_count,observed_at) VALUES"
            " (:observation,:attempt,:sequence,:kind,:digest,:count,:now)"
        ), values)
        return AppendedManifestHandoffObservation(
            observation_id, attempt_id, sequence, kind, now, facts
        )

    @staticmethod
    def _validate_history(rows) -> ManifestHandoffObservationKind:
        if not rows:
            raise ManifestHandoffRegistryUnavailable
        latest = ManifestHandoffObservationKind.RESERVED
        for expected, row in enumerate(rows, 1):
            try:
                observation_id = ManifestHandoffObservationId(
                    _decode(row.observation_id)
                )
                kind = ManifestHandoffObservationKind(row.kind)
                facts = _facts(row.manifest_sha256, row.file_count)
                _ = _utc(row.observed_at)
            except (TypeError, ValueError):
                raise ManifestHandoffRegistryUnavailable from None
            if row.sequence_number != expected:
                raise ManifestHandoffRegistryUnavailable
            if expected == 1 and kind is not ManifestHandoffObservationKind.RESERVED:
                raise ManifestHandoffRegistryUnavailable
            if expected > 1:
                try:
                    AppendedManifestHandoffObservation(
                        observation_id,
                        ManifestHandoffAttemptId("stored-history-validation"),
                        expected,
                        kind,
                        _utc(row.observed_at),
                        facts,
                    )
                except ValueError:
                    raise ManifestHandoffRegistryUnavailable from None
                if not DatabaseManifestHandoffObservationAppend._transition_allowed(
                    latest, kind
                ):
                    raise ManifestHandoffRegistryUnavailable
            elif facts is not None:
                raise ManifestHandoffRegistryUnavailable
            latest = kind
        return latest

    @staticmethod
    def _transition_allowed(previous, following) -> bool:
        if following is ManifestHandoffObservationKind.WRITER_STARTED:
            return previous is ManifestHandoffObservationKind.RESERVED
        if following in {
            ManifestHandoffObservationKind.WRITER_HANDED_OFF,
            ManifestHandoffObservationKind.WRITER_OUTCOME_UNKNOWN,
        }:
            return previous is ManifestHandoffObservationKind.WRITER_STARTED
        if following in _RECONCILIATIONS:
            return previous is not ManifestHandoffObservationKind.RESERVED
        if following in {
            ManifestHandoffObservationKind.CLEANUP_COMPLETED,
            ManifestHandoffObservationKind.CLEANUP_OUTCOME_UNKNOWN,
        }:
            return previous is (
                ManifestHandoffObservationKind.MANIFEST_HANDED_OFF_PENDING_CLEANUP
            )
        return False

    @staticmethod
    def _retry(rows, observation_id, attempt_id, kind, facts, values):
        if len(rows) != 1:
            raise ManifestHandoffRegistryUnavailable
        row = rows[0]
        stored_facts = _facts(row.manifest_sha256, row.file_count)
        if (
            row.observation_id != values["observation"]
            or row.attempt_id != values["attempt"]
            or row.kind != values["kind"]
            or stored_facts != facts
        ):
            return ManifestHandoffObservationConflict()
        try:
            sequence = row.sequence_number
            observed_at = _utc(row.observed_at)
            stored_kind = ManifestHandoffObservationKind(row.kind)
            if type(sequence) is not int or sequence < 2:
                raise ValueError
            return AppendedManifestHandoffObservation(
                observation_id, attempt_id, sequence, stored_kind, observed_at, facts
            )
        except (TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None
