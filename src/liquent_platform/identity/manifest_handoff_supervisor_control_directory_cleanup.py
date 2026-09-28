"""Closed values for retained supervisor control-directory cleanup."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .access import UserId
from .manifest_handoff_supervisor_control_directory import (
    RetiredManifestHandoffSupervisorControlDirectory,
)
from .manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)


def _require_id(value: object, message: str) -> None:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(message)


def _require_utc(value: object, message: str) -> None:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() != timezone.utc.utcoffset(value)
    ):
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupAttemptId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory cleanup attempt id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryRetentionDecisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory retention decision id is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "manifest handoff supervisor control directory retention policy revision id is invalid")


class ManifestHandoffSupervisorControlDirectoryCleanupDisposition(str, Enum):
    RETAIN = "retain"
    ELIGIBLE = "eligible"


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupDecision:
    retired: RetiredManifestHandoffSupervisorControlDirectory = field(repr=False)
    decision_id: ManifestHandoffSupervisorControlDirectoryRetentionDecisionId = field(repr=False)
    policy_revision_id: ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId = field(repr=False)
    disposition: ManifestHandoffSupervisorControlDirectoryCleanupDisposition
    decided_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.retired) is RetiredManifestHandoffSupervisorControlDirectory,
            type(self.decision_id) is ManifestHandoffSupervisorControlDirectoryRetentionDecisionId,
            type(self.policy_revision_id) is ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
            type(self.disposition) is ManifestHandoffSupervisorControlDirectoryCleanupDisposition,
        )):
            raise ValueError("manifest handoff supervisor control directory cleanup decision is invalid")
        _require_utc(self.decided_at, "manifest handoff supervisor control directory cleanup decision is invalid")
        if self.decided_at < self.retired.retired_at:
            raise ValueError("manifest handoff supervisor control directory cleanup decision is invalid")

    @property
    def directory_id(self):
        return self.retired.directory_id


@dataclass(frozen=True, slots=True)
class CleanupManifestHandoffSupervisorControlDirectory:
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    actor_user_id: UserId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.attempt_id) is ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
            type(self.actor_user_id) is str and bool(self.actor_user_id),
            type(self.directory_id) is ManifestHandoffSupervisorControlDirectoryId,
        )):
            raise ValueError("manifest handoff supervisor control directory cleanup request is invalid")


class ManifestHandoffSupervisorControlDirectoryCleanupOutcome(str, Enum):
    REMOVED = "removed"
    ALREADY_ABSENT = "already_absent"


@dataclass(frozen=True, slots=True)
class CompletedManifestHandoffSupervisorControlDirectoryCleanup:
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    outcome: ManifestHandoffSupervisorControlDirectoryCleanupOutcome
    completed_at: datetime

    def __post_init__(self) -> None:
        _validate_attempt_binding(self)
        if type(self.outcome) is not ManifestHandoffSupervisorControlDirectoryCleanupOutcome:
            raise ValueError("manifest handoff supervisor control directory cleanup result is invalid")
        _require_utc(self.completed_at, "manifest handoff supervisor control directory cleanup result is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired:
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_attempt_binding(self)


@dataclass(frozen=True, slots=True)
class ReconcileManifestHandoffSupervisorControlDirectoryCleanup:
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)

    def __post_init__(self) -> None:
        _validate_attempt_binding(self)


class ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome(str, Enum):
    ABSENT = "absent"
    PRESENT = "present"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class ReconciledManifestHandoffSupervisorControlDirectoryCleanup:
    attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId = field(repr=False)
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)
    outcome: ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome
    reconciled_at: datetime

    def __post_init__(self) -> None:
        _validate_attempt_binding(self)
        if type(self.outcome) is not ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome:
            raise ValueError("manifest handoff supervisor control directory cleanup reconciliation is invalid")
        _require_utc(self.reconciled_at, "manifest handoff supervisor control directory cleanup reconciliation is invalid")


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorControlDirectoryCleanupConflict:
    """Detail-free denied, divergent, retained, or unsafe cleanup facts."""


def _validate_attempt_binding(value: object) -> None:
    if not all((
        type(value.attempt_id) is ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
        type(value.directory_id) is ManifestHandoffSupervisorControlDirectoryId,
    )):
        raise ValueError("manifest handoff supervisor control directory cleanup binding is invalid")
