"""Closed values for authoritative supervisor cleanup retention evaluation."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .manifest_handoff_supervisor_control_directory import (
    RetiredManifestHandoffSupervisorControlDirectory,
)
from .manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryCleanupDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupDisposition,
    ManifestHandoffSupervisorControlDirectoryRetentionDecisionId,
    ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
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
class ManifestHandoffSupervisorCleanupRetentionOperationId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_id(self.value, "supervisor cleanup retention operation id is invalid")


class ManifestHandoffSupervisorCleanupRetentionDataClass(str, Enum):
    SUPERVISOR_CONTROL_DIRECTORY = "supervisor_control_directory"


@dataclass(frozen=True, slots=True)
class EvaluateManifestHandoffSupervisorControlDirectoryRetention:
    operation_id: ManifestHandoffSupervisorCleanupRetentionOperationId = field(
        repr=False
    )
    directory_id: ManifestHandoffSupervisorControlDirectoryId = field(repr=False)

    def __post_init__(self) -> None:
        if not all((
            type(self.operation_id)
            is ManifestHandoffSupervisorCleanupRetentionOperationId,
            type(self.directory_id)
            is ManifestHandoffSupervisorControlDirectoryId,
        )):
            raise ValueError("supervisor cleanup retention request is invalid")


@dataclass(frozen=True, slots=True)
class EvaluatedManifestHandoffSupervisorControlDirectoryRetention:
    request: EvaluateManifestHandoffSupervisorControlDirectoryRetention = field(
        repr=False
    )
    retired: RetiredManifestHandoffSupervisorControlDirectory = field(repr=False)
    data_class: ManifestHandoffSupervisorCleanupRetentionDataClass
    policy_revision_id: ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId = field(
        repr=False
    )
    disposition: ManifestHandoffSupervisorControlDirectoryCleanupDisposition
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not all((
            type(self.request)
            is EvaluateManifestHandoffSupervisorControlDirectoryRetention,
            type(self.retired)
            is RetiredManifestHandoffSupervisorControlDirectory,
            self.request.directory_id == self.retired.directory_id,
            type(self.data_class)
            is ManifestHandoffSupervisorCleanupRetentionDataClass,
            type(self.policy_revision_id)
            is ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
            type(self.disposition)
            is ManifestHandoffSupervisorControlDirectoryCleanupDisposition,
        )):
            raise ValueError("supervisor cleanup retention evaluation is invalid")
        _require_utc(
            self.evaluated_at,
            "supervisor cleanup retention evaluation is invalid",
        )
        if self.evaluated_at < self.retired.retired_at:
            raise ValueError("supervisor cleanup retention evaluation is invalid")


@dataclass(frozen=True, slots=True)
class BindManifestHandoffSupervisorControlDirectoryRetentionDecision:
    evaluation: EvaluatedManifestHandoffSupervisorControlDirectoryRetention = field(
        repr=False
    )
    decision_id: ManifestHandoffSupervisorControlDirectoryRetentionDecisionId = field(
        repr=False
    )

    def __post_init__(self) -> None:
        if not all((
            type(self.evaluation)
            is EvaluatedManifestHandoffSupervisorControlDirectoryRetention,
            type(self.decision_id)
            is ManifestHandoffSupervisorControlDirectoryRetentionDecisionId,
        )):
            raise ValueError("supervisor cleanup retention decision binding is invalid")


@dataclass(frozen=True, slots=True)
class BoundManifestHandoffSupervisorControlDirectoryRetentionDecision:
    evaluation: EvaluatedManifestHandoffSupervisorControlDirectoryRetention = field(
        repr=False
    )
    decision: ManifestHandoffSupervisorControlDirectoryCleanupDecision = field(
        repr=False
    )

    def __post_init__(self) -> None:
        if not all((
            type(self.evaluation)
            is EvaluatedManifestHandoffSupervisorControlDirectoryRetention,
            type(self.decision)
            is ManifestHandoffSupervisorControlDirectoryCleanupDecision,
            self.decision.retired == self.evaluation.retired,
            self.decision.policy_revision_id
            == self.evaluation.policy_revision_id,
            self.decision.disposition == self.evaluation.disposition,
            self.decision.decided_at == self.evaluation.evaluated_at,
        )):
            raise ValueError("bound supervisor cleanup retention decision is invalid")

    @property
    def operation_id(self):
        return self.evaluation.request.operation_id


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorCleanupRetentionOperationConflict:
    """Detail-free reused, divergent, stale, or incompatible operation."""
