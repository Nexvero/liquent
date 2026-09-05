"""Atomic current-authority preflight for one publication attempt."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.release_publication import (
    PreparedReleasePublicationAttempt,
    ReleasePublicationAttemptId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationExecutorId,
    ReleasePublicationHandoffId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationAttemptConflict,
    ReleasePublicationAttemptUnavailable,
)


_LOCK = text(
    "LOCK TABLE release_registry_current_set,release_registry_set_revisions,"
    " release_registry_revision_signers,release_registry_revision_keys,"
    " release_publication_channels,release_publication_channel_revisions,"
    " release_publication_revision_publishers,release_publication_current_channels,"
    " release_publication_handoffs,release_publication_receipts,"
    " release_publication_reassessments,release_publication_executors,"
    " release_publication_executions,release_publication_execution_attempts"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_EXISTING = text(
    "SELECT execution.handoff_id,execution.executor_id,"
    " execution.publisher_authority_id,execution.channel_id,"
    " execution.channel_revision_id,execution.bundle_sha256,"
    " execution.signature_sha256,execution.status,attempt.attempt_id,"
    " attempt.attempt_number,attempt.status AS attempt_status"
    " FROM release_publication_executions execution"
    " LEFT JOIN release_publication_execution_attempts attempt"
    " ON attempt.execution_id=execution.execution_id"
    " WHERE execution.execution_id=:execution"
)
_CURRENT = text(
    "SELECT handoff.bundle_sha256,handoff.wheel_sha256,"
    " handoff.checksums_sha256,handoff.signature_sha256,"
    " handoff.promotion_evidence_sha256"
    " FROM release_publication_handoffs handoff"
    " JOIN release_publication_executors executor"
    " ON executor.executor_id=:executor"
    " JOIN release_publication_current_channels current_channel"
    " ON current_channel.channel_id=handoff.channel_id"
    " AND current_channel.revision_id=handoff.channel_revision_id"
    " JOIN release_publication_channel_revisions channel_revision"
    " ON channel_revision.revision_id=current_channel.revision_id"
    " AND channel_revision.channel_id=current_channel.channel_id"
    " AND channel_revision.status='active'"
    " AND channel_revision.artifact_class='operational_bundle'"
    " AND channel_revision.package_name='liquent'"
    " JOIN release_publication_revision_publishers publisher"
    " ON publisher.revision_id=current_channel.revision_id"
    " AND publisher.channel_id=current_channel.channel_id"
    " AND publisher.authority_id=handoff.publisher_authority_id"
    " AND publisher.status='active'"
    " JOIN release_registry_current_set current_registry"
    " ON current_registry.singleton_key=1"
    " JOIN release_registry_set_revisions registry_revision"
    " ON registry_revision.revision_id=current_registry.revision_id"
    " AND registry_revision.policy_status='active'"
    " JOIN release_registry_revision_signers signer"
    " ON signer.revision_id=current_registry.revision_id"
    " AND signer.authority_id=handoff.signer_authority_id"
    " AND signer.status='active'"
    " JOIN release_registry_revision_keys signing_key"
    " ON signing_key.revision_id=current_registry.revision_id"
    " AND signing_key.key_id=handoff.key_id"
    " AND signing_key.signer_authority_id=handoff.signer_authority_id"
    " AND signing_key.status='active'"
    " WHERE handoff.handoff_id=:handoff"
    " AND handoff.publisher_authority_id=:publisher"
    " AND handoff.channel_id=:channel"
    " AND handoff.channel_revision_id=:channel_revision"
    " AND handoff.status='ready_for_publication'"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_receipts receipt"
    " WHERE receipt.handoff_id=handoff.handoff_id)"
    " AND NOT EXISTS (SELECT 1 FROM release_publication_reassessments reassessment"
    " WHERE reassessment.handoff_id=handoff.handoff_id"
    " AND reassessment.status='pending')"
)
_HEX = re.compile(r"[0-9a-f]{64}").fullmatch


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise ReleasePublicationAttemptUnavailable
    return value.encode("utf-8")


class DatabaseReleasePublicationAttemptPreflight:
    """Commit a prepared attempt only while every authority is current."""

    __slots__ = ("_engine", "_executor_id", "_generate_attempt_id", "_clock")

    def __init__(
        self,
        engine: Engine,
        *,
        executor_id: ReleasePublicationExecutorId,
        generate_attempt_id: Callable[[], ReleasePublicationAttemptId],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if type(executor_id) is not ReleasePublicationExecutorId:
            raise ReleasePublicationAttemptUnavailable
        self._engine = engine
        self._executor_id = executor_id
        self._generate_attempt_id = generate_attempt_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationAttemptPreflight()"

    def prepare_attempt(
        self, execution_id, handoff_id, publisher_authority_id, channel_id,
        expected_channel_revision,
    ):
        try:
            if not all((
                type(execution_id) is ReleasePublicationExecutionId,
                type(handoff_id) is ReleasePublicationHandoffId,
                type(publisher_authority_id) is ReleasePublisherAuthorityId,
                type(channel_id) is ReleasePublicationChannelId,
                type(expected_channel_revision)
                is ReleasePublicationChannelPolicyRevisionId,
            )):
                raise ReleasePublicationAttemptUnavailable
            values = {
                "execution": _encode(execution_id.value),
                "handoff": _encode(handoff_id.value),
                "executor": _encode(self._executor_id.value),
                "publisher": _encode(publisher_authority_id.value),
                "channel": _encode(channel_id.value),
                "channel_revision": _encode(expected_channel_revision.value),
            }
            with self._engine.begin() as transaction:
                return self._prepare(transaction, execution_id, handoff_id, values)
        except (ReleasePublicationAttemptConflict, ReleasePublicationAttemptUnavailable) as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleasePublicationAttemptUnavailable

    def _prepare(self, transaction: Connection, execution_id, handoff_id, values):
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise ReleasePublicationAttemptUnavailable
        existing = transaction.execute(_EXISTING, values).all()
        if existing:
            return self._retry(execution_id, handoff_id, values, existing)
        if transaction.execute(text(
            "SELECT 1 FROM release_publication_executions WHERE handoff_id=:handoff"
        ), values).first() is not None:
            raise ReleasePublicationAttemptConflict
        current = transaction.execute(_CURRENT, values).first()
        if current is None:
            return None
        if any(type(value) is not str or _HEX(value) is None for value in current):
            raise ReleasePublicationAttemptUnavailable
        attempt_id = self._generate_attempt_id()
        now = self._clock()
        if type(attempt_id) is not ReleasePublicationAttemptId:
            raise ReleasePublicationAttemptUnavailable
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ReleasePublicationAttemptUnavailable
        values.update({
            "attempt": _encode(attempt_id.value),
            "bundle": current.bundle_sha256,
            "signature": current.signature_sha256,
            "now": now.astimezone(timezone.utc),
        })
        transaction.execute(text(
            "INSERT INTO release_publication_executions VALUES "
            "(:execution,:handoff,:executor,:publisher,:channel,:channel_revision,"
            ":bundle,:signature,'prepared',:now)"
        ), values)
        transaction.execute(text(
            "INSERT INTO release_publication_execution_attempts VALUES "
            "(:attempt,:execution,1,'prepared',:now,NULL)"
        ), values)
        return PreparedReleasePublicationAttempt(execution_id, attempt_id, handoff_id, 1)

    def _retry(self, execution_id, handoff_id, values, rows):
        if len(rows) != 1:
            raise ReleasePublicationAttemptUnavailable
        row = rows[0]
        expected = (
            values["handoff"], values["executor"], values["publisher"],
            values["channel"], values["channel_revision"],
        )
        actual = (
            row.handoff_id, row.executor_id, row.publisher_authority_id,
            row.channel_id, row.channel_revision_id,
        )
        if actual != expected:
            raise ReleasePublicationAttemptConflict
        if row.status != "prepared" or row.attempt_status != "prepared" or row.attempt_number != 1:
            return None
        if _HEX(row.bundle_sha256) is None or _HEX(row.signature_sha256) is None:
            raise ReleasePublicationAttemptUnavailable
        try:
            attempt_id = ReleasePublicationAttemptId(bytes(row.attempt_id).decode("utf-8"))
        except (UnicodeError, ValueError, TypeError):
            raise ReleasePublicationAttemptUnavailable from None
        return PreparedReleasePublicationAttempt(execution_id, attempt_id, handoff_id, 1)
