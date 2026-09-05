"""Stable identities for the release-publication control plane."""

from dataclasses import dataclass, field
from enum import Enum


def _require(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ReleasePublicationHandoffId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication handoff id")


@dataclass(frozen=True, slots=True)
class ReleasePublisherAuthorityId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publisher authority id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationChannelId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication channel id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationChannelPolicyRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication channel policy revision id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationDecisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication decision id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationProviderReceiptId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication provider receipt id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationReassessmentId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication reassessment id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationBootstrapId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication bootstrap id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationExecutorId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication executor id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationExecutorRegistrationId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication executor registration id")


@dataclass(frozen=True, slots=True)
class RegisteredReleasePublicationExecutor:
    registration_id: ReleasePublicationExecutorRegistrationId = field(repr=False)
    executor_id: ReleasePublicationExecutorId = field(repr=False)


@dataclass(frozen=True, slots=True)
class ReleasePublicationExecutionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication execution id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationAttemptId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication attempt id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationRecoveryId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.value, "release publication recovery id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationChannelDefinition:
    package_name: str
    provider_kind: str
    target_name: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.package_name, "release publication package name")
        _require(self.provider_kind, "release publication provider kind")
        _require(self.target_name, "release publication target name")


@dataclass(frozen=True, slots=True)
class BootstrappedReleasePublicationControlPlane:
    bootstrap_id: ReleasePublicationBootstrapId = field(repr=False)
    publisher_authority_id: ReleasePublisherAuthorityId = field(repr=False)
    channel_id: ReleasePublicationChannelId = field(repr=False)
    channel_revision_id: ReleasePublicationChannelPolicyRevisionId = field(repr=False)


@dataclass(frozen=True, slots=True)
class AcceptedReleasePublicationHandoff:
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    decision_id: ReleasePublicationDecisionId = field(repr=False)
    channel_id: ReleasePublicationChannelId = field(repr=False)
    channel_revision_id: ReleasePublicationChannelPolicyRevisionId = field(repr=False)


@dataclass(frozen=True, slots=True)
class PreparedReleasePublicationAttempt:
    execution_id: ReleasePublicationExecutionId = field(repr=False)
    attempt_id: ReleasePublicationAttemptId = field(repr=False)
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    attempt_number: int

    def __post_init__(self) -> None:
        if type(self.attempt_number) is not int or self.attempt_number < 1:
            raise ValueError("release publication attempt number must be positive")


@dataclass(frozen=True, slots=True)
class ReleasePublicationArtifactBinding:
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    bundle_sha256: str = field(repr=False)
    signature_sha256: str = field(repr=False)
    promotion_evidence_sha256: str = field(repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.bundle_sha256, "bundle sha256"),
            (self.signature_sha256, "signature sha256"),
            (self.promotion_evidence_sha256, "promotion evidence sha256"),
        ):
            _require(value, name)


@dataclass(frozen=True, slots=True)
class ReleasePublicationArtifactBytes:
    bundle_filename: str
    bundle: bytes = field(repr=False)
    signature: bytes = field(repr=False)
    promotion_evidence: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.bundle_filename, "bundle filename")
        for value, name in (
            (self.bundle, "bundle"),
            (self.signature, "signature"),
            (self.promotion_evidence, "promotion evidence"),
        ):
            if type(value) is not bytes or not value:
                raise ValueError(f"release publication {name} must be non-empty bytes")


@dataclass(frozen=True, slots=True)
class VerifiedReleasePublicationArtifacts:
    execution_id: ReleasePublicationExecutionId = field(repr=False)
    attempt_id: ReleasePublicationAttemptId = field(repr=False)
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    package_version: str
    bundle_sha256: str
    wheel_sha256: str
    checksums_sha256: str
    signature_sha256: str
    promotion_evidence_sha256: str
    artifacts: ReleasePublicationArtifactBytes = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.package_version, "release publication package version")


@dataclass(frozen=True, slots=True)
class ReleasePublicationTarget:
    channel_id: ReleasePublicationChannelId = field(repr=False)
    channel_revision_id: ReleasePublicationChannelPolicyRevisionId = field(repr=False)
    provider_kind: str
    target_name: str = field(repr=False)
    package_name: str
    package_version: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.provider_kind, "provider kind"),
            (self.target_name, "target name"),
            (self.package_name, "package name"),
            (self.package_version, "package version"),
        ):
            _require(value, f"release publication {name}")


@dataclass(frozen=True, slots=True)
class ReleasePublicationTargetObservation:
    canonical_artifact_id: str = field(repr=False)
    provider_revision: str = field(repr=False)
    package_name: str
    package_version: str
    wheel_sha256: str
    visible: bool

    def __post_init__(self) -> None:
        for value, name in (
            (self.canonical_artifact_id, "canonical artifact id"),
            (self.provider_revision, "provider revision"),
            (self.package_name, "observed package name"),
            (self.package_version, "observed package version"),
            (self.wheel_sha256, "observed wheel sha256"),
        ):
            _require(value, f"release publication {name}")
        if type(self.visible) is not bool:
            raise ValueError("release publication visibility must be boolean")


class ReleasePublicationTargetDecisionKind(Enum):
    CREATE_ALLOWED = "create_allowed"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class InspectedReleasePublicationTarget:
    kind: ReleasePublicationTargetDecisionKind
    target: ReleasePublicationTarget
    artifacts: VerifiedReleasePublicationArtifacts = field(repr=False)
    observation: ReleasePublicationTargetObservation | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not ReleasePublicationTargetDecisionKind:
            raise ValueError("release publication target decision kind is invalid")
        if (self.kind is ReleasePublicationTargetDecisionKind.CREATE_ALLOWED) != (
            self.observation is None
        ):
            raise ValueError("release publication target decision observation is invalid")


@dataclass(frozen=True, slots=True)
class ReleasePublicationCreateAcknowledgement:
    provider_request_id: str = field(repr=False)

    def __post_init__(self) -> None:
        _require(self.provider_request_id, "release publication provider request id")


@dataclass(frozen=True, slots=True)
class ReleasePublicationWritePendingReconciliation:
    execution_id: ReleasePublicationExecutionId = field(repr=False)
    attempt_id: ReleasePublicationAttemptId = field(repr=False)
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    acknowledgement: ReleasePublicationCreateAcknowledgement | None = field(
        default=None, repr=False
    )


class ReleasePublicationReconciliationKind(Enum):
    PUBLISHED_CONFIRMED = "published_confirmed"
    ABSENCE_CONFIRMED = "absence_confirmed"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class ReconciledReleasePublicationOutcome:
    execution_id: ReleasePublicationExecutionId = field(repr=False)
    attempt_id: ReleasePublicationAttemptId = field(repr=False)
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    kind: ReleasePublicationReconciliationKind
    target: ReleasePublicationTarget
    current_authority: bool
    observation: ReleasePublicationTargetObservation | None = field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        if type(self.kind) is not ReleasePublicationReconciliationKind:
            raise ValueError("release publication reconciliation kind is invalid")
        if type(self.current_authority) is not bool:
            raise ValueError("release publication current authority must be boolean")
        if (self.kind is ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED) != (
            self.observation is None
        ):
            raise ValueError("release publication reconciliation observation is invalid")


class ReleasePublicationFinalStatus(Enum):
    PUBLISHED = "published"
    PUBLISHED_REASSESSMENT_REQUIRED = "published_reassessment_required"


@dataclass(frozen=True, slots=True)
class FinalizedReleasePublication:
    receipt_id: ReleasePublicationProviderReceiptId = field(repr=False)
    execution_id: ReleasePublicationExecutionId = field(repr=False)
    attempt_id: ReleasePublicationAttemptId = field(repr=False)
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    status: ReleasePublicationFinalStatus
    reassessment_id: ReleasePublicationReassessmentId | None = field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        if type(self.status) is not ReleasePublicationFinalStatus:
            raise ValueError("release publication final status is invalid")
        required = (
            self.status
            is ReleasePublicationFinalStatus.PUBLISHED_REASSESSMENT_REQUIRED
        )
        if required != (self.reassessment_id is not None):
            raise ValueError("release publication final reassessment is invalid")


@dataclass(frozen=True, slots=True)
class FinalizedReleasePublicationRecovery:
    recovery_id: ReleasePublicationRecoveryId = field(repr=False)
    execution_id: ReleasePublicationExecutionId = field(repr=False)
    attempt_id: ReleasePublicationAttemptId = field(repr=False)
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    kind: ReleasePublicationReconciliationKind
    retry_eligible: bool
    reassessment_id: ReleasePublicationReassessmentId | None = field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        if self.kind not in {
            ReleasePublicationReconciliationKind.ABSENCE_CONFIRMED,
            ReleasePublicationReconciliationKind.CONFLICT,
        }:
            raise ValueError("release publication recovery kind is invalid")
        if type(self.retry_eligible) is not bool:
            raise ValueError("release publication retry eligibility must be boolean")
        if self.kind is ReleasePublicationReconciliationKind.CONFLICT:
            if self.retry_eligible or self.reassessment_id is None:
                raise ValueError("release publication conflict recovery is invalid")
        elif self.reassessment_id is not None:
            raise ValueError("release publication absence recovery is invalid")


class ReleasePublicationWorkStateKind(Enum):
    NOT_ACTIONABLE = "not_actionable"
    ATTEMPT_ONE_PREPARED = "attempt_one_prepared"
    ATTEMPT_ONE_UNKNOWN = "attempt_one_unknown"
    ATTEMPT_ONE_ABSENCE_RECOVERED = "attempt_one_absence_recovered"
    ATTEMPT_TWO_PREPARED = "attempt_two_prepared"
    ATTEMPT_TWO_UNKNOWN = "attempt_two_unknown"
    TERMINAL = "terminal"


class ReleasePublicationWorkResultKind(Enum):
    PUBLISHED = "published"
    PUBLISHED_REASSESSMENT_REQUIRED = "published_reassessment_required"
    NOT_PUBLISHED = "not_published"
    PUBLICATION_CONFLICT = "publication_conflict"
    PENDING_RECONCILIATION = "pending_reconciliation"
    NOT_ACTIONABLE = "not_actionable"


@dataclass(frozen=True, slots=True)
class ReleasePublicationWorkRequest:
    execution_id: ReleasePublicationExecutionId = field(repr=False)
    handoff_id: ReleasePublicationHandoffId = field(repr=False)
    publisher_authority_id: ReleasePublisherAuthorityId = field(repr=False)
    channel_id: ReleasePublicationChannelId = field(repr=False)
    expected_channel_revision: ReleasePublicationChannelPolicyRevisionId = field(
        repr=False
    )


@dataclass(frozen=True, slots=True)
class ReleasePublicationWorkState:
    kind: ReleasePublicationWorkStateKind
    attempt_id: ReleasePublicationAttemptId | None = field(default=None, repr=False)
    terminal_result: ReleasePublicationWorkResultKind | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ReleasePublicationWorkStateKind:
            raise ValueError("release publication work state kind is invalid")
        terminal = self.kind is ReleasePublicationWorkStateKind.TERMINAL
        neutral = self.kind is ReleasePublicationWorkStateKind.NOT_ACTIONABLE
        if terminal != (self.terminal_result is not None):
            raise ValueError("release publication terminal work state is invalid")
        if (terminal or neutral) == (self.attempt_id is not None):
            raise ValueError("release publication work attempt binding is invalid")
        if self.terminal_result in {
            ReleasePublicationWorkResultKind.PENDING_RECONCILIATION,
            ReleasePublicationWorkResultKind.NOT_ACTIONABLE,
        }:
            raise ValueError("release publication terminal result is invalid")


@dataclass(frozen=True, slots=True)
class ReleasePublicationWorkResult:
    kind: ReleasePublicationWorkResultKind

    def __post_init__(self) -> None:
        if type(self.kind) is not ReleasePublicationWorkResultKind:
            raise ValueError("release publication work result kind is invalid")
