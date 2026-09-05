"""Ports required by the identity and authorization capability."""

from datetime import timedelta
from typing import Protocol

from liquent_platform.identity.access import (
    BootstrappedIdentityAuthority,
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.lifecycle import (
    AnchoredIdentityLifecycleFoundation,
    AnchoredUserLifecycleAuthoritySet,
    AnchoredWorkspaceLifecycleAuthoritySet,
    AuthorizedUserLifecycleAuthorityChange,
    AuthorizedWorkspaceLifecycleAuthorityChange,
    LifecycleAuthorityIntent,
    UserLifecycleAuthorityChangeId,
    UserLifecycleAuthoritySetRevisionId,
    WorkspaceLifecycleAuthorityChangeId,
    WorkspaceLifecycleAuthoritySetRevisionId,
    AuthorizedUserLifecycleChange,
    UserLifecycleChangeId,
    UserLifecycleIntent,
    UserLifecycleRevisionId,
    AuthorizedWorkspaceLifecycleChange,
    WorkspaceLifecycleChangeId,
    WorkspaceLifecycleIntent,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
)
from liquent_platform.identity.oidc_trust import (
    ActiveOidcTrustSnapshot,
    AnchoredOidcTrustAuthoritySet,
    AuthorizedOidcTrustAuthorityLifecycleChange,
    AuthorizedOidcTrustChange,
    BootstrappedOidcTrustAuthority,
    OidcTrustChangeId,
    OidcTrustChangeKind,
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityLifecycleIntent,
    OidcTrustAuthoritySetRevisionId,
    OidcTrustAuthorityRecoveryId,
    RecoveredOidcTrustAuthoritySet,
    OidcTrustRevisionId,
)
from liquent_platform.identity.membership_management import (
    AnchoredWorkspaceMembershipAuthoritySet,
    AuthorizedWorkspaceMembershipAuthorityLifecycleChange,
    AuthorizedWorkspaceMembershipChange,
    BootstrappedWorkspaceMembershipManagementAuthority,
    WorkspaceMembershipChangeId,
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityLifecycleIntent,
    WorkspaceMembershipAuthoritySetRevisionId,
    WorkspaceMembershipAuthorityRecoveryId,
    RecoveredWorkspaceMembershipAuthoritySet,
    WorkspaceMembershipRevisionId,
)
from liquent_platform.identity.manifest_handoff import (
    AppendedManifestHandoffRecoveryObservation,
    AppendedManifestHandoffObservation,
    ClaimedManifestHandoffExecution,
    ClaimedManifestHandoffRecovery,
    ManifestHandoffAttemptId,
    ManifestHandoffAttemptView,
    ManifestHandoffCompositionConflict,
    ManifestHandoffCompositionRequest,
    ManifestHandoffCompositionResult,
    ManifestHandoffFacts,
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionEndId,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffLeaseRenewalId,
    ManifestHandoffName,
    ManifestHandoffObservationConflict,
    ManifestHandoffObservationId,
    ManifestHandoffOwnershipConflict,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryEndId,
    ManifestHandoffRecoveryOwnerId,
    ManifestHandoffRecoveryRequest,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffReservationConflict,
    ManifestHandoffReservationId,
    ReservedManifestHandoffAttempt,
    ManifestHandoffScopeBinding,
    RecordedManifestHandoffExecutionEnd,
    RecordedManifestHandoffRecoveryEnd,
    RenewedManifestHandoffExecutionLease,
    StartedManifestHandoffExecution,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess,
    CompletedManifestHandoffWriterProcess,
    ManifestHandoffRecoverySupervisorRequest,
    ManifestHandoffSupervisorConflict,
    ManifestHandoffSupervisorHandleId,
    ManifestHandoffWriterSupervisorRequest,
    PreparedManifestHandoffRecoveryProcess,
    PreparedManifestHandoffWriterProcess,
    RunningManifestHandoffRecoveryProcess,
    RunningManifestHandoffWriterProcess,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    BindManifestHandoffSupervisorHandle,
    BoundManifestHandoffSupervisorHandle,
    ManifestHandoffSupervisorBackend,
    ManifestHandoffSupervisorCorrelationConflict,
    ManifestHandoffSupervisorPrepareId,
    ManifestHandoffSupervisorReleaseId,
    ManifestHandoffSupervisorTerminateId,
    ManifestHandoffSupervisorTerminalObservationId,
    RecordManifestHandoffSupervisorRelease,
    RecordManifestHandoffSupervisorTermination,
    RecordManifestHandoffSupervisorTerminalObservation,
    RecordedManifestHandoffSupervisorRelease,
    RecordedManifestHandoffSupervisorTermination,
    RecordedManifestHandoffSupervisorTerminalObservation,
    ReserveManifestHandoffRecoveryPreparation,
    ReserveManifestHandoffWriterPreparation,
    ReservedManifestHandoffRecoveryPreparation,
    ReservedManifestHandoffWriterPreparation,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    CommitManifestHandoffSupervisorGateRelease,
    CommitManifestHandoffSupervisorLaunch,
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalConflict,
    ManifestHandoffWriterJournalView,
    RecordManifestHandoffRecoveryJournalTerminal,
    RecordManifestHandoffSupervisorGated,
    RecordManifestHandoffSupervisorRunning,
    RecordManifestHandoffWriterJournalTerminal,
    RegisterManifestHandoffRecoveryJournalJob,
    RegisterManifestHandoffWriterJournalJob,
    RequestManifestHandoffSupervisorTermination,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    BindManifestHandoffSupervisorRuntime,
    BoundManifestHandoffSupervisorRuntime,
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorCreationId,
    ManifestHandoffSupervisorRuntimeConflict,
    RecordManifestHandoffSupervisorReadyArtifact,
    RecordManifestHandoffSupervisorReleaseConsumedArtifact,
    RecordManifestHandoffSupervisorReleaseTokenArtifact,
    RecordManifestHandoffSupervisorTerminalEnvelopeArtifact,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    ActivateManifestHandoffSupervisorControlDirectory,
    ActiveManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryConflict,
    ManifestHandoffSupervisorControlDirectoryLifecycle,
    ReserveManifestHandoffSupervisorControlDirectory,
    ReservedManifestHandoffSupervisorControlDirectory,
    RetireManifestHandoffSupervisorControlDirectory,
    RetiredManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    CleanupManifestHandoffSupervisorControlDirectory,
    CompletedManifestHandoffSupervisorControlDirectoryCleanup,
    ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
    ManifestHandoffSupervisorControlDirectoryCleanupDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired,
    ReconcileManifestHandoffSupervisorControlDirectoryCleanup,
    ReconciledManifestHandoffSupervisorControlDirectoryCleanup,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention import (
    BindManifestHandoffSupervisorControlDirectoryRetentionDecision,
    BoundManifestHandoffSupervisorControlDirectoryRetentionDecision,
    EvaluateManifestHandoffSupervisorControlDirectoryRetention,
    EvaluatedManifestHandoffSupervisorControlDirectoryRetention,
    ManifestHandoffSupervisorCleanupRetentionOperationId,
    ManifestHandoffSupervisorCleanupRetentionOperationConflict,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention_policy import (
    ActiveManifestHandoffSupervisorCleanupRetentionPolicy,
    BootstrapManifestHandoffSupervisorCleanupRetentionPolicy,
    BootstrappedManifestHandoffSupervisorCleanupRetentionPolicy,
    ChangeManifestHandoffSupervisorCleanupRetentionPolicy,
    ChangedManifestHandoffSupervisorCleanupRetentionPolicy,
    ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet,
    ManifestHandoffSupervisorCleanupRetentionPolicyConflict,
    RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    ClearedManifestHandoffSupervisorControlDirectoryCleanup,
    ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority,
    ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_execution import (
    AbsentManifestHandoffSupervisorControlDirectoryCleanupPreflight,
    ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup,
    ClaimedManifestHandoffSupervisorControlDirectoryCleanup,
    InspectedManifestHandoffSupervisorControlDirectoryCleanupReconciliation,
    PreflightManifestHandoffSupervisorControlDirectoryCleanup,
    PreparedManifestHandoffSupervisorControlDirectoryCleanup,
    RemovedManifestHandoffSupervisorControlDirectory,
    UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance_mutation import (
    ChangeManifestHandoffSupervisorControlDirectoryCleanupHold,
    ChangeManifestHandoffSupervisorControlDirectoryCleanupManagement,
    ChangeManifestHandoffSupervisorControlDirectoryCleanupRecovery,
    ChangeManifestHandoffSupervisorControlDirectoryCleanupReference,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupHoldChange,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupManagementChange,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupRecoveryChange,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupReferenceChange,
    ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_mutation_authority import (
    BootstrapCleanupHoldMutationAuthority,
    BootstrapCleanupManagementMutationAuthority,
    BootstrapCleanupRecoveryMutationAuthority,
    BootstrapCleanupReferenceMutationAuthority,
    ChangeCleanupHoldMutationAuthority,
    ChangeCleanupManagementMutationAuthority,
    ChangeCleanupRecoveryMutationAuthority,
    ChangeCleanupReferenceMutationAuthority,
    CleanupHoldMutationAuthoritySet,
    CleanupManagementMutationAuthoritySet,
    CleanupRecoveryMutationAuthoritySet,
    CleanupReferenceMutationAuthoritySet,
    ManifestHandoffSupervisorCleanupMutationAuthorityConflict,
    RecoverCleanupHoldMutationAuthority,
    RecoverCleanupManagementMutationAuthority,
    RecoverCleanupRecoveryMutationAuthority,
    RecoverCleanupReferenceMutationAuthority,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    AcceptedManifestHandoffSupervisorTermination,
    CreateManifestHandoffSupervisorContainer,
    CreatedManifestHandoffSupervisorContainer,
    InspectManifestHandoffSupervisorContainer,
    ManifestHandoffSupervisorEngineConflict,
    ObservedManifestHandoffSupervisorContainer,
    StartManifestHandoffSupervisorContainer,
    StartedManifestHandoffSupervisorContainer,
    TerminateManifestHandoffSupervisorContainer,
    WaitManifestHandoffSupervisorContainer,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    EncodedManifestHandoffSupervisorControlArtifact,
    ManifestHandoffSupervisorControlArtifactConflict,
    ManifestHandoffSupervisorControlDocument,
    PublishManifestHandoffSupervisorControlArtifact,
    PublishedManifestHandoffSupervisorControlArtifact,
    ReadManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    AcceptedManifestHandoffSupervisorReleaseToken,
    CompleteManifestHandoffSupervisorGateWrapper,
    CompletedManifestHandoffSupervisorGateWrapper,
    ManifestHandoffSupervisorGateWrapperConflict,
    ReadyManifestHandoffSupervisorGateWrapper,
    ReleasedManifestHandoffSupervisorGateWrapper,
    StartManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_executor import (
    ExecuteManifestHandoffRecoveryCapability,
    ExecuteManifestHandoffWriterCapability,
    ExecutedManifestHandoffRecoveryCapability,
    ExecutedManifestHandoffWriterCapability,
)
from liquent_platform.identity.manifest_handoff_supervisor_capability_outcome import (
    InspectManifestHandoffRecoveryCapabilityOutcome,
    InspectManifestHandoffWriterCapabilityOutcome,
    ManifestHandoffRecoveryCapabilityOutcomeObservation,
    ManifestHandoffWriterCapabilityOutcomeObservation,
)
from liquent_platform.identity.manifest_handoff_supervisor_service import (
    InspectManifestHandoffSupervisorService,
    ManifestHandoffRecoveryServiceResult,
    ManifestHandoffSupervisorServiceConflict,
    ManifestHandoffSupervisorGateBindingConflict,
    ManifestHandoffWriterServiceResult,
    PrepareManifestHandoffRecoveryService,
    PrepareManifestHandoffWriterService,
    ReleaseManifestHandoffSupervisorService,
    TerminateManifestHandoffSupervisorService,
)
from liquent_platform.identity.onboarding import (
    AuthorizedOnboardingDecision,
    OnboardingDecisionId,
)
from liquent_platform.application.experiment import ExperimentSnapshot
from liquent_platform.identity.research import (
    JobId,
    ResearchJobAcceptanceId,
    ResearchJobClaimId,
    ResearchJobRevisionId,
    ResearchWorkerId,
    WorkspaceId,
)
from liquent_platform.identity.research_job import (
    AcceptedResearchJob,
    ClaimedResearchJob,
    CompletedResearchJob,
    RenewedResearchJobLease,
    ResearchJobAcceptanceConflict,
    ResearchJobView,
    ResearchJobFailureCode,
    ResearchResultArtifactClass,
)
from liquent_platform.identity.release_authority import (
    ActivatedReleaseSigningKey,
    ReleaseActivationReviewerId,
    BootstrappedReleaseRegistry,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistrySetRevisionId,
    ReleaseSigningDecisionId,
    SignedReleaseCandidate,
    ReleaseSigningKeyId,
    ReleaseSigningPublicKey,
)
from liquent_platform.identity.release_publication import (
    AcceptedReleasePublicationHandoff,
    BootstrappedReleasePublicationControlPlane,
    ReleasePublicationBootstrapId,
    ReleasePublicationChannelDefinition,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationDecisionId,
    ReleasePublicationHandoffId,
    ReleasePublisherAuthorityId,
    PreparedReleasePublicationAttempt,
    ReleasePublicationArtifactBinding,
    ReleasePublicationArtifactBytes,
    ReleasePublicationExecutionId,
    ReleasePublicationExecutorRegistrationId,
    RegisteredReleasePublicationExecutor,
    ReleasePublicationAttemptId,
    VerifiedReleasePublicationArtifacts,
    InspectedReleasePublicationTarget,
    ReleasePublicationTarget,
    ReleasePublicationTargetObservation,
    ReleasePublicationCreateAcknowledgement,
    ReleasePublicationWritePendingReconciliation,
    ReconciledReleasePublicationOutcome,
    FinalizedReleasePublication,
    FinalizedReleasePublicationRecovery,
    ReleasePublicationWorkRequest,
    ReleasePublicationWorkState,
)
from liquent_platform.identity.release_publication_provider import (
    PackageIndexArtifactRecord,
    PackageIndexCreateRecord,
    PackageIndexProviderConfiguration,
)
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    IssuedBrowserSession,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)


class WorkspaceMembershipLookup(Protocol):
    """Find the membership for one user and one workspace."""

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership | None: ...


class AuthorizedManifestHandoffAttemptReservation(Protocol):
    """Reserve one permanent scoped name after resolving current authority."""

    def reserve_attempt(
        self,
        reservation_id: ManifestHandoffReservationId,
        actor_user_id: UserId,
        scope_id: ManifestHandoffRegistryScopeId,
        handoff_name: ManifestHandoffName,
    ) -> ReservedManifestHandoffAttempt | ManifestHandoffReservationConflict | None: ...


class AuthorizedManifestHandoffAttemptLookup(Protocol):
    """Read one named attempt after resolving current scoped authority."""

    def get_attempt(
        self,
        actor_user_id: UserId,
        scope_id: ManifestHandoffRegistryScopeId,
        handoff_name: ManifestHandoffName,
    ) -> ManifestHandoffAttemptView | None: ...


class ManifestHandoffScopeBindingLookup(Protocol):
    """Resolve one stable controlled source/target binding without caller paths."""

    def get_binding(
        self, scope_id: ManifestHandoffRegistryScopeId
    ) -> ManifestHandoffScopeBinding | None: ...


class ControlledManifestHandoffComposition(Protocol):
    """Run one registry-bound writer composition without caller outcomes."""

    def handoff(
        self, request: ManifestHandoffCompositionRequest
    ) -> ManifestHandoffCompositionResult | ManifestHandoffCompositionConflict | None: ...


_ObservationAppendResult = (
    AppendedManifestHandoffObservation | ManifestHandoffObservationConflict | None
)


class ControlledManifestHandoffWriterObservationAppend(Protocol):
    """Append only direct, internally controlled writer observations."""

    def record_writer_started(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
    ) -> _ObservationAppendResult: ...

    def record_writer_handed_off(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
        facts: ManifestHandoffFacts,
    ) -> _ObservationAppendResult: ...

    def record_writer_outcome_unknown(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
    ) -> _ObservationAppendResult: ...


class ControlledManifestHandoffReconciliationObservationAppend(Protocol):
    """Append one outcome produced directly by fresh read-only reconciliation."""

    def record_manifest_absent(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
    ) -> _ObservationAppendResult: ...

    def record_manifest_temporary_only(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
        facts: ManifestHandoffFacts,
    ) -> _ObservationAppendResult: ...

    def record_manifest_handed_off(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
        facts: ManifestHandoffFacts,
    ) -> _ObservationAppendResult: ...

    def record_manifest_handed_off_pending_cleanup(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
        facts: ManifestHandoffFacts,
    ) -> _ObservationAppendResult: ...

    def record_manifest_handoff_conflict(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
    ) -> _ObservationAppendResult: ...


class ControlledManifestHandoffCleanupObservationAppend(Protocol):
    """Append only direct, internally controlled cleanup observations."""

    def record_cleanup_completed(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
        facts: ManifestHandoffFacts,
    ) -> _ObservationAppendResult: ...

    def record_cleanup_outcome_unknown(
        self,
        observation_id: ManifestHandoffObservationId,
        attempt_id: ManifestHandoffAttemptId,
    ) -> _ObservationAppendResult: ...


_OwnershipResult = ManifestHandoffOwnershipConflict | None


class AuthorizedManifestHandoffExecutionClaim(Protocol):
    """Claim one reserved attempt for one controlled execution owner."""

    def claim_execution(
        self,
        claim_id: ManifestHandoffExecutionClaimId,
        attempt_id: ManifestHandoffAttemptId,
        actor_user_id: UserId,
        owner_id: ManifestHandoffExecutionOwnerId,
    ) -> ClaimedManifestHandoffExecution | ManifestHandoffOwnershipConflict | None: ...


class ManifestHandoffExecutionLeaseRenewal(Protocol):
    """Renew liveness without granting takeover or recovery."""

    def renew_execution_lease(
        self,
        renewal_id: ManifestHandoffLeaseRenewalId,
        claim_id: ManifestHandoffExecutionClaimId,
        owner_id: ManifestHandoffExecutionOwnerId,
    ) -> RenewedManifestHandoffExecutionLease | ManifestHandoffOwnershipConflict | None: ...


class ControlledManifestHandoffClaimedWriterStart(Protocol):
    """Bind writer_started to the one current execution claim."""

    def start_claimed_execution(
        self,
        observation_id: ManifestHandoffObservationId,
        claim_id: ManifestHandoffExecutionClaimId,
        owner_id: ManifestHandoffExecutionOwnerId,
    ) -> StartedManifestHandoffExecution | ManifestHandoffOwnershipConflict | None: ...


class ControlledManifestHandoffExecutionEnd(Protocol):
    """Record only direct source-specific terminal supervisor facts."""

    def record_outcome_secured(
        self,
        end_id: ManifestHandoffExecutionEndId,
        claim_id: ManifestHandoffExecutionClaimId,
        owner_id: ManifestHandoffExecutionOwnerId,
    ) -> RecordedManifestHandoffExecutionEnd | _OwnershipResult: ...

    def record_outcome_unknown(
        self,
        end_id: ManifestHandoffExecutionEndId,
        claim_id: ManifestHandoffExecutionClaimId,
        owner_id: ManifestHandoffExecutionOwnerId,
    ) -> RecordedManifestHandoffExecutionEnd | _OwnershipResult: ...

    def record_start_not_confirmed(
        self,
        end_id: ManifestHandoffExecutionEndId,
        claim_id: ManifestHandoffExecutionClaimId,
        owner_id: ManifestHandoffExecutionOwnerId,
    ) -> RecordedManifestHandoffExecutionEnd | _OwnershipResult: ...


class AuthorizedManifestHandoffRecoveryClaim(Protocol):
    """Claim read-only recovery after current authority and terminal evidence."""

    def claim_recovery(
        self, request: ManifestHandoffRecoveryRequest
    ) -> ClaimedManifestHandoffRecovery | ManifestHandoffOwnershipConflict | None: ...


class ControlledManifestHandoffRecoveryEnd(Protocol):
    """Record only direct terminal outcomes of one controlled recovery owner."""

    def record_outcome_secured(
        self,
        end_id: ManifestHandoffRecoveryEndId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
    ) -> RecordedManifestHandoffRecoveryEnd | _OwnershipResult: ...

    def record_outcome_unknown(
        self,
        end_id: ManifestHandoffRecoveryEndId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
    ) -> RecordedManifestHandoffRecoveryEnd | _OwnershipResult: ...

    def record_start_not_confirmed(
        self,
        end_id: ManifestHandoffRecoveryEndId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
    ) -> RecordedManifestHandoffRecoveryEnd | _OwnershipResult: ...


class ControlledManifestHandoffRecoveryObservationAppend(Protocol):
    """Append only fresh reconciliation facts bound to one recovery claim."""

    def record_manifest_absent(
        self,
        observation_id: ManifestHandoffObservationId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
    ) -> AppendedManifestHandoffRecoveryObservation | _OwnershipResult: ...

    def record_manifest_temporary_only(
        self,
        observation_id: ManifestHandoffObservationId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
        facts: ManifestHandoffFacts,
    ) -> AppendedManifestHandoffRecoveryObservation | _OwnershipResult: ...

    def record_manifest_handed_off(
        self,
        observation_id: ManifestHandoffObservationId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
        facts: ManifestHandoffFacts,
    ) -> AppendedManifestHandoffRecoveryObservation | _OwnershipResult: ...

    def record_manifest_handed_off_pending_cleanup(
        self,
        observation_id: ManifestHandoffObservationId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
        facts: ManifestHandoffFacts,
    ) -> AppendedManifestHandoffRecoveryObservation | _OwnershipResult: ...

    def record_manifest_handoff_conflict(
        self,
        observation_id: ManifestHandoffObservationId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
    ) -> AppendedManifestHandoffRecoveryObservation | _OwnershipResult: ...


_WriterSupervisorState = (
    PreparedManifestHandoffWriterProcess
    | RunningManifestHandoffWriterProcess
    | CompletedManifestHandoffWriterProcess
)
_RecoverySupervisorState = (
    PreparedManifestHandoffRecoveryProcess
    | RunningManifestHandoffRecoveryProcess
    | CompletedManifestHandoffRecoveryProcess
)


class ControlledManifestHandoffWriterSupervisor(Protocol):
    """Supervise only one fixed start-gated writer capability."""

    def prepare_writer(
        self, request: ManifestHandoffWriterSupervisorRequest
    ) -> PreparedManifestHandoffWriterProcess | ManifestHandoffSupervisorConflict | None: ...

    def release_writer(
        self,
        handle_id: ManifestHandoffSupervisorHandleId,
        claim_id: ManifestHandoffExecutionClaimId,
        owner_id: ManifestHandoffExecutionOwnerId,
    ) -> _WriterSupervisorState | ManifestHandoffSupervisorConflict | None: ...

    def inspect_writer(
        self,
        handle_id: ManifestHandoffSupervisorHandleId,
        claim_id: ManifestHandoffExecutionClaimId,
        owner_id: ManifestHandoffExecutionOwnerId,
    ) -> _WriterSupervisorState | ManifestHandoffSupervisorConflict | None: ...

    def terminate_writer(
        self,
        handle_id: ManifestHandoffSupervisorHandleId,
        claim_id: ManifestHandoffExecutionClaimId,
        owner_id: ManifestHandoffExecutionOwnerId,
    ) -> RunningManifestHandoffWriterProcess | CompletedManifestHandoffWriterProcess | ManifestHandoffSupervisorConflict | None: ...


class ControlledManifestHandoffRecoverySupervisor(Protocol):
    """Supervise only one fixed start-gated read-only reconciler capability."""

    def prepare_recovery(
        self, request: ManifestHandoffRecoverySupervisorRequest
    ) -> PreparedManifestHandoffRecoveryProcess | ManifestHandoffSupervisorConflict | None: ...

    def release_recovery(
        self,
        handle_id: ManifestHandoffSupervisorHandleId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
    ) -> _RecoverySupervisorState | ManifestHandoffSupervisorConflict | None: ...

    def inspect_recovery(
        self,
        handle_id: ManifestHandoffSupervisorHandleId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
    ) -> _RecoverySupervisorState | ManifestHandoffSupervisorConflict | None: ...

    def terminate_recovery(
        self,
        handle_id: ManifestHandoffSupervisorHandleId,
        claim_id: ManifestHandoffRecoveryClaimId,
        owner_id: ManifestHandoffRecoveryOwnerId,
    ) -> RunningManifestHandoffRecoveryProcess | CompletedManifestHandoffRecoveryProcess | ManifestHandoffSupervisorConflict | None: ...


_SupervisorPreparation = (
    ReservedManifestHandoffWriterPreparation
    | ReservedManifestHandoffRecoveryPreparation
)


class CurrentManifestHandoffSupervisorBackend(Protocol):
    """Resolve the current active controlled backend without caller selection."""

    def resolve(self) -> ManifestHandoffSupervisorBackend | None: ...


class ManifestHandoffSupervisorCorrelationStore(Protocol):
    """Append stable platform correlations; never operate a process."""

    def reserve_writer(
        self, request: ReserveManifestHandoffWriterPreparation
    ) -> ReservedManifestHandoffWriterPreparation | ManifestHandoffSupervisorCorrelationConflict | None: ...

    def reserve_recovery(
        self, request: ReserveManifestHandoffRecoveryPreparation
    ) -> ReservedManifestHandoffRecoveryPreparation | ManifestHandoffSupervisorCorrelationConflict | None: ...

    def bind_handle(
        self, request: BindManifestHandoffSupervisorHandle
    ) -> BoundManifestHandoffSupervisorHandle | ManifestHandoffSupervisorCorrelationConflict | None: ...

    def record_release(
        self, request: RecordManifestHandoffSupervisorRelease
    ) -> RecordedManifestHandoffSupervisorRelease | ManifestHandoffSupervisorCorrelationConflict | None: ...

    def record_termination(
        self, request: RecordManifestHandoffSupervisorTermination
    ) -> RecordedManifestHandoffSupervisorTermination | ManifestHandoffSupervisorCorrelationConflict | None: ...

    def record_terminal_observation(
        self, request: RecordManifestHandoffSupervisorTerminalObservation
    ) -> RecordedManifestHandoffSupervisorTerminalObservation | ManifestHandoffSupervisorCorrelationConflict | None: ...


class ManifestHandoffSupervisorCorrelationLookup(Protocol):
    """Resolve only exact stable identities without mutation or adoption."""

    def resolve_preparation(
        self, prepare_id: ManifestHandoffSupervisorPrepareId
    ) -> _SupervisorPreparation | None: ...

    def resolve_handle(
        self, prepare_id: ManifestHandoffSupervisorPrepareId
    ) -> BoundManifestHandoffSupervisorHandle | None: ...

    def resolve_release(
        self, release_id: ManifestHandoffSupervisorReleaseId
    ) -> RecordedManifestHandoffSupervisorRelease | None: ...

    def resolve_termination(
        self, terminate_id: ManifestHandoffSupervisorTerminateId
    ) -> RecordedManifestHandoffSupervisorTermination | None: ...

    def resolve_terminal_observation(
        self, terminal_observation_id: ManifestHandoffSupervisorTerminalObservationId
    ) -> RecordedManifestHandoffSupervisorTerminalObservation | None: ...


class ManifestHandoffWriterSupervisorJournal(Protocol):
    """Persist only closed writer-journal transitions."""

    def register_writer(self, request: RegisterManifestHandoffWriterJournalJob) -> ManifestHandoffWriterJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def commit_writer_launch(self, request: CommitManifestHandoffSupervisorLaunch) -> ManifestHandoffWriterJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def record_writer_gated(self, request: RecordManifestHandoffSupervisorGated) -> ManifestHandoffWriterJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def commit_writer_release(self, request: CommitManifestHandoffSupervisorGateRelease) -> ManifestHandoffWriterJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def record_writer_running(self, request: RecordManifestHandoffSupervisorRunning) -> ManifestHandoffWriterJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def request_writer_termination(self, request: RequestManifestHandoffSupervisorTermination) -> ManifestHandoffWriterJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def record_writer_terminal(self, request: RecordManifestHandoffWriterJournalTerminal) -> ManifestHandoffWriterJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def inspect_writer_journal(self, handle_id: ManifestHandoffSupervisorHandleId) -> ManifestHandoffWriterJournalView | None: ...


class ManifestHandoffRecoverySupervisorJournal(Protocol):
    """Persist only closed read-only recovery-journal transitions."""

    def register_recovery(self, request: RegisterManifestHandoffRecoveryJournalJob) -> ManifestHandoffRecoveryJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def commit_recovery_launch(self, request: CommitManifestHandoffSupervisorLaunch) -> ManifestHandoffRecoveryJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def record_recovery_gated(self, request: RecordManifestHandoffSupervisorGated) -> ManifestHandoffRecoveryJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def commit_recovery_release(self, request: CommitManifestHandoffSupervisorGateRelease) -> ManifestHandoffRecoveryJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def record_recovery_running(self, request: RecordManifestHandoffSupervisorRunning) -> ManifestHandoffRecoveryJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def request_recovery_termination(self, request: RequestManifestHandoffSupervisorTermination) -> ManifestHandoffRecoveryJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def record_recovery_terminal(self, request: RecordManifestHandoffRecoveryJournalTerminal) -> ManifestHandoffRecoveryJournalView | ManifestHandoffSupervisorJournalConflict | None: ...
    def inspect_recovery_journal(self, handle_id: ManifestHandoffSupervisorHandleId) -> ManifestHandoffRecoveryJournalView | None: ...


class ManifestHandoffSupervisorRuntimeBindingStore(Protocol):
    def bind_runtime(
        self, request: BindManifestHandoffSupervisorRuntime
    ) -> BoundManifestHandoffSupervisorRuntime | ManifestHandoffSupervisorRuntimeConflict | None: ...


class ManifestHandoffSupervisorRuntimeBindingLookup(Protocol):
    def resolve_runtime(
        self, handle_id: ManifestHandoffSupervisorHandleId
    ) -> BoundManifestHandoffSupervisorRuntime | None: ...

    def resolve_creation(
        self, creation_id: ManifestHandoffSupervisorCreationId
    ) -> BoundManifestHandoffSupervisorRuntime | None: ...


class ManifestHandoffSupervisorControlArtifactStore(Protocol):
    def record_ready(self, request: RecordManifestHandoffSupervisorReadyArtifact) -> RecordedManifestHandoffSupervisorControlArtifact | ManifestHandoffSupervisorRuntimeConflict | None: ...
    def record_release_token(self, request: RecordManifestHandoffSupervisorReleaseTokenArtifact) -> RecordedManifestHandoffSupervisorControlArtifact | ManifestHandoffSupervisorRuntimeConflict | None: ...
    def record_release_consumed(self, request: RecordManifestHandoffSupervisorReleaseConsumedArtifact) -> RecordedManifestHandoffSupervisorControlArtifact | ManifestHandoffSupervisorRuntimeConflict | None: ...
    def record_terminal_envelope(self, request: RecordManifestHandoffSupervisorTerminalEnvelopeArtifact) -> RecordedManifestHandoffSupervisorControlArtifact | ManifestHandoffSupervisorRuntimeConflict | None: ...


class ManifestHandoffSupervisorControlArtifactLookup(Protocol):
    def resolve_artifact(
        self, artifact_id: ManifestHandoffSupervisorControlArtifactId
    ) -> RecordedManifestHandoffSupervisorControlArtifact | None: ...

    def resolve_artifact_role(
        self,
        handle_id: ManifestHandoffSupervisorHandleId,
        role: ManifestHandoffSupervisorControlArtifactRole,
    ) -> RecordedManifestHandoffSupervisorControlArtifact | None: ...


class ManifestHandoffSupervisorEngine(Protocol):
    """Operate only the configured local engine and closed runtime profiles."""

    def create(
        self, request: CreateManifestHandoffSupervisorContainer
    ) -> CreatedManifestHandoffSupervisorContainer | ManifestHandoffSupervisorEngineConflict | None: ...

    def inspect(
        self, request: InspectManifestHandoffSupervisorContainer
    ) -> ObservedManifestHandoffSupervisorContainer | ManifestHandoffSupervisorEngineConflict | None: ...

    def start(
        self, request: StartManifestHandoffSupervisorContainer
    ) -> StartedManifestHandoffSupervisorContainer | ManifestHandoffSupervisorEngineConflict | None: ...

    def wait_terminal(
        self, request: WaitManifestHandoffSupervisorContainer
    ) -> ObservedManifestHandoffSupervisorContainer | ManifestHandoffSupervisorEngineConflict | None: ...

    def terminate(
        self, request: TerminateManifestHandoffSupervisorContainer
    ) -> AcceptedManifestHandoffSupervisorTermination | ManifestHandoffSupervisorEngineConflict | None: ...


class ManifestHandoffSupervisorControlArtifactCodec(Protocol):
    def encode(
        self, document: ManifestHandoffSupervisorControlDocument
    ) -> EncodedManifestHandoffSupervisorControlArtifact: ...

    def decode(
        self, artifact: EncodedManifestHandoffSupervisorControlArtifact
    ) -> ManifestHandoffSupervisorControlDocument: ...


class ManifestHandoffSupervisorControlArtifactPublisher(Protocol):
    def publish(
        self, request: PublishManifestHandoffSupervisorControlArtifact
    ) -> PublishedManifestHandoffSupervisorControlArtifact | ManifestHandoffSupervisorControlArtifactConflict: ...


class ManifestHandoffSupervisorControlArtifactReader(Protocol):
    def read(
        self, request: ReadManifestHandoffSupervisorControlArtifact
    ) -> EncodedManifestHandoffSupervisorControlArtifact | None: ...


class ManifestHandoffSupervisorGateWrapper(Protocol):
    def publish_ready(
        self, request: StartManifestHandoffSupervisorGateWrapper
    ) -> ReadyManifestHandoffSupervisorGateWrapper | ManifestHandoffSupervisorGateWrapperConflict: ...

    def await_release(
        self, ready: ReadyManifestHandoffSupervisorGateWrapper
    ) -> AcceptedManifestHandoffSupervisorReleaseToken | None: ...

    def publish_consumed(
        self, token: AcceptedManifestHandoffSupervisorReleaseToken
    ) -> ReleasedManifestHandoffSupervisorGateWrapper | ManifestHandoffSupervisorGateWrapperConflict: ...

    def publish_terminal(
        self, request: CompleteManifestHandoffSupervisorGateWrapper
    ) -> CompletedManifestHandoffSupervisorGateWrapper | ManifestHandoffSupervisorGateWrapperConflict: ...


class ManifestHandoffSupervisorCapabilityExecutor(Protocol):
    def execute_writer(
        self, request: ExecuteManifestHandoffWriterCapability
    ) -> ExecutedManifestHandoffWriterCapability: ...

    def execute_recovery(
        self, request: ExecuteManifestHandoffRecoveryCapability
    ) -> ExecutedManifestHandoffRecoveryCapability: ...


class ManifestHandoffSupervisorCapabilityOutcomeInspection(Protocol):
    def inspect_writer_outcome(
        self, request: InspectManifestHandoffWriterCapabilityOutcome
    ) -> ManifestHandoffWriterCapabilityOutcomeObservation: ...

    def inspect_recovery_outcome(
        self, request: InspectManifestHandoffRecoveryCapabilityOutcome
    ) -> ManifestHandoffRecoveryCapabilityOutcomeObservation: ...


class ManifestHandoffSupervisorCapabilityOutcomeWait(Protocol):
    def wait_writer_outcome(
        self, request: InspectManifestHandoffWriterCapabilityOutcome
    ) -> ExecutedManifestHandoffWriterCapability: ...

    def wait_recovery_outcome(
        self, request: InspectManifestHandoffRecoveryCapabilityOutcome
    ) -> ExecutedManifestHandoffRecoveryCapability: ...


class PersistentManifestHandoffWriterSupervisorService(Protocol):
    def prepare_writer(self, command: PrepareManifestHandoffWriterService) -> ManifestHandoffWriterServiceResult | ManifestHandoffSupervisorServiceConflict | None: ...
    def release_writer(self, command: ReleaseManifestHandoffSupervisorService) -> ManifestHandoffWriterServiceResult | ManifestHandoffSupervisorServiceConflict | None: ...
    def terminate_writer(self, command: TerminateManifestHandoffSupervisorService) -> ManifestHandoffWriterServiceResult | ManifestHandoffSupervisorServiceConflict | None: ...
    def inspect_writer(self, command: InspectManifestHandoffSupervisorService) -> ManifestHandoffWriterServiceResult | None: ...


class PersistentManifestHandoffRecoverySupervisorService(Protocol):
    def prepare_recovery(self, command: PrepareManifestHandoffRecoveryService) -> ManifestHandoffRecoveryServiceResult | ManifestHandoffSupervisorServiceConflict | None: ...
    def release_recovery(self, command: ReleaseManifestHandoffSupervisorService) -> ManifestHandoffRecoveryServiceResult | ManifestHandoffSupervisorServiceConflict | None: ...
    def terminate_recovery(self, command: TerminateManifestHandoffSupervisorService) -> ManifestHandoffRecoveryServiceResult | ManifestHandoffSupervisorServiceConflict | None: ...
    def inspect_recovery(self, command: InspectManifestHandoffSupervisorService) -> ManifestHandoffRecoveryServiceResult | None: ...


class ManifestHandoffSupervisorGateBindingStore(Protocol):
    def bind_gate(
        self, binding: StartManifestHandoffSupervisorGateWrapper
    ) -> StartManifestHandoffSupervisorGateWrapper | ManifestHandoffSupervisorGateBindingConflict | None: ...


class ManifestHandoffSupervisorGateBindingLookup(Protocol):
    def resolve_gate(
        self, handle_id: ManifestHandoffSupervisorHandleId
    ) -> StartManifestHandoffSupervisorGateWrapper | None: ...

    def resolve_gate_artifact(
        self, artifact_id: ManifestHandoffSupervisorControlArtifactId
    ) -> StartManifestHandoffSupervisorGateWrapper | None: ...


class ManifestHandoffSupervisorControlDirectoryLifecycleStore(Protocol):
    def reserve_control_directory(
        self, request: ReserveManifestHandoffSupervisorControlDirectory
    ) -> ReservedManifestHandoffSupervisorControlDirectory | ManifestHandoffSupervisorControlDirectoryConflict | None: ...

    def activate_control_directory(
        self, request: ActivateManifestHandoffSupervisorControlDirectory
    ) -> ActiveManifestHandoffSupervisorControlDirectory | ManifestHandoffSupervisorControlDirectoryConflict | None: ...

    def retire_control_directory(
        self, request: RetireManifestHandoffSupervisorControlDirectory
    ) -> RetiredManifestHandoffSupervisorControlDirectory | ManifestHandoffSupervisorControlDirectoryConflict | None: ...


class ManifestHandoffSupervisorControlDirectoryLifecycleLookup(Protocol):
    def resolve_control_directory(
        self, directory_id: ManifestHandoffSupervisorControlDirectoryId
    ) -> ManifestHandoffSupervisorControlDirectoryLifecycle | None: ...

    def resolve_handle_control_directory(
        self, handle_id: ManifestHandoffSupervisorHandleId
    ) -> ManifestHandoffSupervisorControlDirectoryLifecycle | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupDecisionLookup(Protocol):
    def resolve_control_directory_cleanup_decision(
        self, directory_id: ManifestHandoffSupervisorControlDirectoryId
    ) -> ManifestHandoffSupervisorControlDirectoryCleanupDecision | None: ...


class ManifestHandoffSupervisorCleanupRetentionPolicyEvaluation(Protocol):
    def evaluate_control_directory_retention(
        self,
        request: EvaluateManifestHandoffSupervisorControlDirectoryRetention,
        retired: RetiredManifestHandoffSupervisorControlDirectory,
    ) -> EvaluatedManifestHandoffSupervisorControlDirectoryRetention | None: ...


class ManifestHandoffSupervisorCleanupRetentionOperationStore(Protocol):
    def resolve_control_directory_retention_operation(
        self,
        operation_id: ManifestHandoffSupervisorCleanupRetentionOperationId,
    ) -> BoundManifestHandoffSupervisorControlDirectoryRetentionDecision | None: ...

    def bind_control_directory_retention_decision(
        self,
        command: BindManifestHandoffSupervisorControlDirectoryRetentionDecision,
    ) -> BoundManifestHandoffSupervisorControlDirectoryRetentionDecision | ManifestHandoffSupervisorCleanupRetentionOperationConflict | None: ...


class ManifestHandoffSupervisorCleanupRetentionPolicyLookup(Protocol):
    def resolve_active_cleanup_retention_policy(
        self,
    ) -> ActiveManifestHandoffSupervisorCleanupRetentionPolicy | None: ...


class ManifestHandoffSupervisorCleanupRetentionPolicyAdministration(Protocol):
    def bootstrap_cleanup_retention_policy(
        self,
        command: BootstrapManifestHandoffSupervisorCleanupRetentionPolicy,
    ) -> BootstrappedManifestHandoffSupervisorCleanupRetentionPolicy | ManifestHandoffSupervisorCleanupRetentionPolicyConflict | None: ...

    def change_cleanup_retention_policy(
        self,
        principal: SessionPrincipal,
        command: ChangeManifestHandoffSupervisorCleanupRetentionPolicy,
    ) -> ChangedManifestHandoffSupervisorCleanupRetentionPolicy | ManifestHandoffSupervisorCleanupRetentionPolicyConflict | None: ...


class ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityAdministration(Protocol):
    def permits_cleanup_retention_policy_mutation(
        self, principal: SessionPrincipal,
    ) -> bool: ...

    def change_cleanup_retention_policy_authority(
        self,
        principal: SessionPrincipal,
        command: ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
    ) -> ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet | ManifestHandoffSupervisorCleanupRetentionPolicyConflict | None: ...

    def recover_cleanup_retention_policy_authority(
        self,
        command: RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
    ) -> ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet | ManifestHandoffSupervisorCleanupRetentionPolicyConflict | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupExecution(Protocol):
    def cleanup_control_directory(
        self, request: CleanupManifestHandoffSupervisorControlDirectory
    ) -> CompletedManifestHandoffSupervisorControlDirectoryCleanup | ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired | ManifestHandoffSupervisorControlDirectoryCleanupConflict | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupReconciliation(Protocol):
    def reconcile_control_directory_cleanup(
        self, request: ReconcileManifestHandoffSupervisorControlDirectoryCleanup
    ) -> ReconciledManifestHandoffSupervisorControlDirectoryCleanup | ManifestHandoffSupervisorControlDirectoryCleanupConflict | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupPreflight(Protocol):
    def prepare_control_directory_cleanup(
        self, request: PreflightManifestHandoffSupervisorControlDirectoryCleanup
    ) -> PreparedManifestHandoffSupervisorControlDirectoryCleanup | AbsentManifestHandoffSupervisorControlDirectoryCleanupPreflight | ManifestHandoffSupervisorControlDirectoryCleanupConflict | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupWriteClaim(Protocol):
    def claim_control_directory_cleanup_write(
        self, request: ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup
    ) -> ClaimedManifestHandoffSupervisorControlDirectoryCleanup | ManifestHandoffSupervisorControlDirectoryCleanupConflict | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimLookup(Protocol):
    def resolve_control_directory_cleanup_write_claim(
        self, attempt_id: ManifestHandoffSupervisorControlDirectoryCleanupAttemptId
    ) -> ClaimedManifestHandoffSupervisorControlDirectoryCleanup | None: ...


class ManifestHandoffSupervisorControlDirectoryPhysicalCleanup(Protocol):
    def remove_control_directory(
        self, claimed: ClaimedManifestHandoffSupervisorControlDirectoryCleanup
    ) -> RemovedManifestHandoffSupervisorControlDirectory | UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect | ManifestHandoffSupervisorControlDirectoryCleanupConflict: ...


class ManifestHandoffSupervisorControlDirectoryCleanupPhysicalOutcomeStore(Protocol):
    def persist_control_directory_cleanup_physical_outcome(
        self,
        outcome: RemovedManifestHandoffSupervisorControlDirectory | UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect,
    ) -> CompletedManifestHandoffSupervisorControlDirectoryCleanup | ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired | ManifestHandoffSupervisorControlDirectoryCleanupConflict | None: ...


class ManifestHandoffSupervisorControlDirectoryPhysicalCleanupReconciliation(Protocol):
    def inspect_control_directory_cleanup(
        self, request: ReconcileManifestHandoffSupervisorControlDirectoryCleanup
    ) -> InspectedManifestHandoffSupervisorControlDirectoryCleanupReconciliation | ManifestHandoffSupervisorControlDirectoryCleanupConflict | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupManagementLookup(Protocol):
    def resolve_control_directory_cleanup_management(
        self, actor_user_id: UserId, scope_id: ManifestHandoffRegistryScopeId
    ) -> ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupHoldLookup(Protocol):
    def resolve_control_directory_cleanup_hold(
        self, directory_id: ManifestHandoffSupervisorControlDirectoryId
    ) -> ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupRecoveryLookup(Protocol):
    def resolve_control_directory_cleanup_recovery(
        self, directory_id: ManifestHandoffSupervisorControlDirectoryId
    ) -> ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupReferenceLookup(Protocol):
    def resolve_control_directory_cleanup_references(
        self, directory_id: ManifestHandoffSupervisorControlDirectoryId
    ) -> ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision | None: ...


class ManifestHandoffSupervisorControlDirectoryCleanupClearanceResolution(Protocol):
    def resolve_control_directory_cleanup_clearance(
        self, request: CleanupManifestHandoffSupervisorControlDirectory
    ) -> ClearedManifestHandoffSupervisorControlDirectoryCleanup | ManifestHandoffSupervisorControlDirectoryCleanupConflict | None: ...


class AuthorizedManifestHandoffSupervisorControlDirectoryCleanupManagementMutation(Protocol):
    def change_control_directory_cleanup_management(
        self, principal: SessionPrincipal,
        command: ChangeManifestHandoffSupervisorControlDirectoryCleanupManagement,
    ) -> CommittedManifestHandoffSupervisorControlDirectoryCleanupManagementChange | ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict | None: ...


class AuthorizedManifestHandoffSupervisorControlDirectoryCleanupHoldMutation(Protocol):
    def change_control_directory_cleanup_hold(
        self, principal: SessionPrincipal,
        command: ChangeManifestHandoffSupervisorControlDirectoryCleanupHold,
    ) -> CommittedManifestHandoffSupervisorControlDirectoryCleanupHoldChange | ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict | None: ...


class AuthorizedManifestHandoffSupervisorControlDirectoryCleanupRecoveryMutation(Protocol):
    def change_control_directory_cleanup_recovery(
        self, principal: SessionPrincipal,
        command: ChangeManifestHandoffSupervisorControlDirectoryCleanupRecovery,
    ) -> CommittedManifestHandoffSupervisorControlDirectoryCleanupRecoveryChange | ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict | None: ...


class AuthorizedManifestHandoffSupervisorControlDirectoryCleanupReferenceMutation(Protocol):
    def change_control_directory_cleanup_references(
        self, principal: SessionPrincipal,
        command: ChangeManifestHandoffSupervisorControlDirectoryCleanupReference,
    ) -> CommittedManifestHandoffSupervisorControlDirectoryCleanupReferenceChange | ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict | None: ...


class AuthorizedManifestHandoffSupervisorControlDirectoryCleanupClearanceCreation(Protocol):
    def create_control_directory_cleanup_clearance(
        self, principal: SessionPrincipal,
        request: CleanupManifestHandoffSupervisorControlDirectory,
    ) -> ClearedManifestHandoffSupervisorControlDirectoryCleanup | ManifestHandoffSupervisorControlDirectoryCleanupConflict | None: ...


class CleanupManagementMutationAuthorityLookup(Protocol):
    def permits_cleanup_management_mutation(
        self, principal: SessionPrincipal, scope_id: ManifestHandoffRegistryScopeId
    ) -> bool: ...


class CleanupHoldMutationAuthorityLookup(Protocol):
    def permits_cleanup_hold_mutation(
        self, principal: SessionPrincipal, scope_id: ManifestHandoffRegistryScopeId
    ) -> bool: ...


class CleanupRecoveryMutationAuthorityLookup(Protocol):
    def permits_cleanup_recovery_mutation(
        self, principal: SessionPrincipal, scope_id: ManifestHandoffRegistryScopeId
    ) -> bool: ...


class CleanupReferenceMutationAuthorityLookup(Protocol):
    def permits_cleanup_reference_mutation(
        self, principal: SessionPrincipal, scope_id: ManifestHandoffRegistryScopeId
    ) -> bool: ...


class CleanupManagementMutationAuthorityBootstrap(Protocol):
    def bootstrap_cleanup_management_mutation_authority(
        self, command: BootstrapCleanupManagementMutationAuthority
    ) -> CleanupManagementMutationAuthoritySet | None: ...


class CleanupHoldMutationAuthorityBootstrap(Protocol):
    def bootstrap_cleanup_hold_mutation_authority(
        self, command: BootstrapCleanupHoldMutationAuthority
    ) -> CleanupHoldMutationAuthoritySet | None: ...


class CleanupRecoveryMutationAuthorityBootstrap(Protocol):
    def bootstrap_cleanup_recovery_mutation_authority(
        self, command: BootstrapCleanupRecoveryMutationAuthority
    ) -> CleanupRecoveryMutationAuthoritySet | None: ...


class CleanupReferenceMutationAuthorityBootstrap(Protocol):
    def bootstrap_cleanup_reference_mutation_authority(
        self, command: BootstrapCleanupReferenceMutationAuthority
    ) -> CleanupReferenceMutationAuthoritySet | None: ...


class CleanupManagementMutationAuthorityLifecycle(Protocol):
    def change_cleanup_management_mutation_authority(
        self, principal: SessionPrincipal,
        command: ChangeCleanupManagementMutationAuthority,
    ) -> CleanupManagementMutationAuthoritySet | ManifestHandoffSupervisorCleanupMutationAuthorityConflict | None: ...


class CleanupHoldMutationAuthorityLifecycle(Protocol):
    def change_cleanup_hold_mutation_authority(
        self, principal: SessionPrincipal,
        command: ChangeCleanupHoldMutationAuthority,
    ) -> CleanupHoldMutationAuthoritySet | ManifestHandoffSupervisorCleanupMutationAuthorityConflict | None: ...


class CleanupRecoveryMutationAuthorityLifecycle(Protocol):
    def change_cleanup_recovery_mutation_authority(
        self, principal: SessionPrincipal,
        command: ChangeCleanupRecoveryMutationAuthority,
    ) -> CleanupRecoveryMutationAuthoritySet | ManifestHandoffSupervisorCleanupMutationAuthorityConflict | None: ...


class CleanupReferenceMutationAuthorityLifecycle(Protocol):
    def change_cleanup_reference_mutation_authority(
        self, principal: SessionPrincipal,
        command: ChangeCleanupReferenceMutationAuthority,
    ) -> CleanupReferenceMutationAuthoritySet | ManifestHandoffSupervisorCleanupMutationAuthorityConflict | None: ...


class OfflineCleanupManagementMutationAuthorityRecovery(Protocol):
    def recover_cleanup_management_mutation_authority(
        self, command: RecoverCleanupManagementMutationAuthority
    ) -> CleanupManagementMutationAuthoritySet | ManifestHandoffSupervisorCleanupMutationAuthorityConflict | None: ...


class OfflineCleanupHoldMutationAuthorityRecovery(Protocol):
    def recover_cleanup_hold_mutation_authority(
        self, command: RecoverCleanupHoldMutationAuthority
    ) -> CleanupHoldMutationAuthoritySet | ManifestHandoffSupervisorCleanupMutationAuthorityConflict | None: ...


class OfflineCleanupRecoveryMutationAuthorityRecovery(Protocol):
    def recover_cleanup_recovery_mutation_authority(
        self, command: RecoverCleanupRecoveryMutationAuthority
    ) -> CleanupRecoveryMutationAuthoritySet | ManifestHandoffSupervisorCleanupMutationAuthorityConflict | None: ...


class OfflineCleanupReferenceMutationAuthorityRecovery(Protocol):
    def recover_cleanup_reference_mutation_authority(
        self, command: RecoverCleanupReferenceMutationAuthority
    ) -> CleanupReferenceMutationAuthoritySet | ManifestHandoffSupervisorCleanupMutationAuthorityConflict | None: ...


class AuthorizedResearchJobAcceptance(Protocol):
    """Accept one retry-safe job after resolving current write authority."""

    def accept_job(
        self,
        acceptance_id: ResearchJobAcceptanceId,
        actor_user_id: UserId,
        snapshot: ExperimentSnapshot,
        artifact_class: ResearchResultArtifactClass,
    ) -> AcceptedResearchJob | ResearchJobAcceptanceConflict | None: ...


class ResearchJobClaim(Protocol):
    """Atomically claim the next currently authorized queued job."""

    def claim_next(self, worker_id: ResearchWorkerId) -> ClaimedResearchJob | None: ...


class ResearchJobHeartbeat(Protocol):
    """Renew exactly one current non-expired claim without caller time."""

    def heartbeat(
        self,
        job_id: JobId,
        expected_revision: ResearchJobRevisionId,
        worker_id: ResearchWorkerId,
        claim_id: ResearchJobClaimId,
    ) -> RenewedResearchJobLease | None: ...


class ResearchJobFinalization(Protocol):
    """Atomically finish exactly one current, non-expired claim."""

    def finalize_success(
        self,
        job_id: JobId,
        expected_revision: ResearchJobRevisionId,
        worker_id: ResearchWorkerId,
        claim_id: ResearchJobClaimId,
        summary: "BacktestExperimentSummary",
        artifact: "ArtifactReference",
    ) -> CompletedResearchJob | None: ...

    def finalize_failure(
        self,
        job_id: JobId,
        expected_revision: ResearchJobRevisionId,
        worker_id: ResearchWorkerId,
        claim_id: ResearchJobClaimId,
        failure_code: ResearchJobFailureCode,
    ) -> CompletedResearchJob | None: ...


class AuthorizedResearchJobLookup(Protocol):
    """Read one job only after resolving current actor read authority."""

    def get_job(
        self, actor_user_id: UserId, job_id: JobId
    ) -> ResearchJobView | None: ...


class InitialReleaseRegistryBootstrap(Protocol):
    """Create the first release authorities and inactive public key once."""

    def bootstrap(
        self,
        bootstrap_id: ReleaseRegistryBootstrapId,
        public_key: ReleaseSigningPublicKey,
    ) -> BootstrappedReleaseRegistry | None: ...


class InitialReleasePublicationControlPlaneBootstrap(Protocol):
    def bootstrap(
        self,
        bootstrap_id: ReleasePublicationBootstrapId,
        channel: ReleasePublicationChannelDefinition,
    ) -> BootstrappedReleasePublicationControlPlane | None: ...


class ReleasePublicationExecutorRegistration(Protocol):
    def register(
        self, registration_id: ReleasePublicationExecutorRegistrationId
    ) -> RegisteredReleasePublicationExecutor: ...


class AuthorizedReleasePublicationHandoffStore(Protocol):
    def accept_handoff(
        self,
        handoff_id: ReleasePublicationHandoffId,
        decision_id: ReleasePublicationDecisionId,
        publisher_authority_id: ReleasePublisherAuthorityId,
        channel_id: ReleasePublicationChannelId,
        expected_channel_revision: ReleasePublicationChannelPolicyRevisionId,
        bundle_path: str,
        signature_path: str,
        promotion_evidence_path: str,
    ) -> AcceptedReleasePublicationHandoff | None: ...


class ReleasePublicationAttemptPreflight(Protocol):
    """Persist one current-authority-bound attempt before provider access."""

    def prepare_attempt(
        self,
        execution_id: ReleasePublicationExecutionId,
        handoff_id: ReleasePublicationHandoffId,
        publisher_authority_id: ReleasePublisherAuthorityId,
        channel_id: ReleasePublicationChannelId,
        expected_channel_revision: ReleasePublicationChannelPolicyRevisionId,
    ) -> PreparedReleasePublicationAttempt | None: ...


class ReleasePublicationArtifactSource(Protocol):
    """Resolve immutable bytes for one internally constructed hash binding."""

    def load_artifacts(
        self, binding: ReleasePublicationArtifactBinding
    ) -> ReleasePublicationArtifactBytes: ...


class ReleasePublicationArtifactIntegrityCheck(Protocol):
    """Verify one prepared attempt's bytes before any provider access."""

    def verify_artifacts(
        self,
        execution_id: ReleasePublicationExecutionId,
        attempt_id: ReleasePublicationAttemptId,
    ) -> VerifiedReleasePublicationArtifacts | None: ...


class ReleasePublicationTargetInspector(Protocol):
    """Inspect one controlled immutable target without creating anything."""

    def inspect_target(
        self, target: ReleasePublicationTarget
    ) -> ReleasePublicationTargetObservation | None: ...


class ReleasePublicationTargetInspection(Protocol):
    """Decide create, reconciliation, or conflict without provider writes."""

    def inspect_publication_target(
        self,
        execution_id: ReleasePublicationExecutionId,
        attempt_id: ReleasePublicationAttemptId,
    ) -> InspectedReleasePublicationTarget | None: ...


class ReleasePublicationImmutableCreator(Protocol):
    """Create one immutable target without overwrite or mutable aliases."""

    def create_immutable(
        self,
        target: ReleasePublicationTarget,
        artifacts: VerifiedReleasePublicationArtifacts,
        idempotency_key: ReleasePublicationExecutionId,
    ) -> ReleasePublicationCreateAcknowledgement: ...


class ReleasePublicationImmutableCreate(Protocol):
    """Commit write-start before one create and preserve possible effects."""

    def create_publication(
        self,
        execution_id: ReleasePublicationExecutionId,
        attempt_id: ReleasePublicationAttemptId,
    ) -> ReleasePublicationWritePendingReconciliation | None: ...


class ReleasePublicationUnknownOutcomeReconciliation(Protocol):
    """Inspect a possible effect without retrying or persisting success."""

    def reconcile_unknown_outcome(
        self,
        execution_id: ReleasePublicationExecutionId,
        attempt_id: ReleasePublicationAttemptId,
    ) -> ReconciledReleasePublicationOutcome | None: ...


class ReleasePublicationReconciliationFinalizer(Protocol):
    """Persist one confirmed external success and any required reassessment."""

    def finalize_reconciliation(
        self,
        execution_id: ReleasePublicationExecutionId,
        attempt_id: ReleasePublicationAttemptId,
    ) -> FinalizedReleasePublication | None: ...


class ReleasePublicationRecoveryFinalizer(Protocol):
    """Persist confirmed absence or conflict without starting another write."""

    def finalize_recovery(
        self,
        execution_id: ReleasePublicationExecutionId,
        attempt_id: ReleasePublicationAttemptId,
    ) -> FinalizedReleasePublicationRecovery | None: ...


class ReleasePublicationRetryAttemptPreflight(Protocol):
    """Prepare attempt 2 only after recovered absence and fresh checks."""

    def prepare_retry_attempt(
        self,
        execution_id: ReleasePublicationExecutionId,
        recovered_attempt_id: ReleasePublicationAttemptId,
    ) -> PreparedReleasePublicationAttempt | None: ...


class ReleasePublicationRetryImmutableCreator(Protocol):
    """Create once with the retry attempt as the idempotency identity."""

    def create_immutable(
        self,
        target: ReleasePublicationTarget,
        artifacts: VerifiedReleasePublicationArtifacts,
        idempotency_key: ReleasePublicationAttemptId,
    ) -> ReleasePublicationCreateAcknowledgement: ...


class ReleasePublicationRetryImmutableCreate(Protocol):
    """Commit attempt-2 write-start and preserve every possible effect."""

    def create_retry_publication(
        self,
        execution_id: ReleasePublicationExecutionId,
        attempt_id: ReleasePublicationAttemptId,
    ) -> ReleasePublicationWritePendingReconciliation | None: ...


class ReleasePublicationWorkStateLookup(Protocol):
    """Resolve current state while binding every closed work reference."""

    def get_work_state(
        self, request: ReleasePublicationWorkRequest
    ) -> ReleasePublicationWorkState | None: ...


class ReleasePublicationCurrentOutcomeFinalizer(Protocol):
    """Inspect once and persist the matching success or recovery outcome."""

    def finalize_current_outcome(
        self,
        execution_id: ReleasePublicationExecutionId,
        attempt_id: ReleasePublicationAttemptId,
    ) -> FinalizedReleasePublication | FinalizedReleasePublicationRecovery | None: ...


class PackageIndexProviderTransport(Protocol):
    """Provider-specific I/O below the controlled package-index adapter."""

    def inspect_package(
        self,
        configuration: PackageIndexProviderConfiguration,
        target: ReleasePublicationTarget,
    ) -> PackageIndexArtifactRecord | None: ...

    def create_package(
        self,
        configuration: PackageIndexProviderConfiguration,
        target: ReleasePublicationTarget,
        artifacts: VerifiedReleasePublicationArtifacts,
        idempotency_key: str,
    ) -> PackageIndexCreateRecord: ...


class ReleaseKeyProofVerifier(Protocol):
    def verify_proof(
        self, public_key: str, challenge: bytes, proof: bytes
    ) -> bool: ...


class ReleaseKeyActivationApprovalVerifier(Protocol):
    def verify_approval(
        self, challenge: bytes, approval: bytes
    ) -> ReleaseActivationReviewerId | None: ...


class AuthorizedReleaseKeyActivationStore(Protocol):
    def activate_key(
        self,
        change_id: ReleaseRegistryLifecycleChangeId,
        actor_authority_id: ReleaseRegistryLifecycleAuthorityId,
        key_id: ReleaseSigningKeyId,
        expected_revision: ReleaseRegistrySetRevisionId,
        proof: bytes,
        approval: bytes,
    ) -> ActivatedReleaseSigningKey | None: ...


class CurrentReleaseAuthorityRegistryProjection(Protocol):
    """Render the complete current release trust registry without mutation."""

    def project(self) -> bytes | None: ...


class ReleaseSigningKeyProvider(Protocol):
    def fingerprint(self) -> str: ...

    def sign(self, payload: bytes, namespace: str) -> bytes: ...


class ReleaseSignatureVerifier(Protocol):
    def verify(
        self, public_key: str, authority_id: str, payload: bytes, signature: bytes
    ) -> bool: ...


class AuthorizedReleaseSigningStore(Protocol):
    def sign_candidate(
        self,
        decision_id: ReleaseSigningDecisionId,
        key_id: ReleaseSigningKeyId,
        expected_revision: ReleaseRegistrySetRevisionId,
        bundle_path: str,
    ) -> SignedReleaseCandidate | None: ...


class OnboardingManagementAuthorityLookup(Protocol):
    """Resolve one actor's authority for one internally selected target.

    ``principal`` identifies the authenticated actor but grants nothing. The
    implementation must resolve actor, target user, target workspace, their
    active state, and the actor's workspace-scoped management capability from
    its system of record. No caller-supplied role or allow decision is accepted.
    ``False`` neutrally covers absence, inactivity, and missing or revoked
    capability; technical inability must remain distinct.
    """

    def permits_onboarding_management(
        self,
        principal: SessionPrincipal,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
    ) -> bool: ...


class WorkspaceMembershipManagementAuthorityLookup(Protocol):
    """Resolve current management authority for one actor and workspace.

    The principal identifies only the actor. Implementations resolve active
    actor, active workspace, and the dedicated workspace-scoped capability from
    the system of record. No role, permission, membership, or allow boolean is
    accepted; ``False`` neutrally covers absence, inactivity, and revocation.
    """

    def permits_workspace_membership_management(
        self, principal: SessionPrincipal, workspace_id: WorkspaceId
    ) -> bool: ...


class InitialWorkspaceMembershipManagementAuthorityBootstrap(Protocol):
    """Grant the first dedicated manager for one existing workspace, once.

    The offline caller selects only existing internal user and workspace facts.
    ``None`` neutrally covers a closed workspace scope and unknown or inactive
    targets. No membership, permission, role, or allow decision is accepted.
    """

    def bootstrap(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> BootstrappedWorkspaceMembershipManagementAuthority | None: ...


class WorkspaceMembershipAuthoritySetAnchor(Protocol):
    """Anchor existing bootstrap authority for one exact workspace, once."""

    def anchor(
        self,
        change_id: WorkspaceMembershipAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
        workspace_id: WorkspaceId,
    ) -> AnchoredWorkspaceMembershipAuthoritySet | None: ...


class AuthorizedWorkspaceMembershipAuthorityLifecycleStore(Protocol):
    """Atomically authorize one regular workspace authority transition."""

    def change_authority(
        self,
        change_id: WorkspaceMembershipAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        workspace_id: WorkspaceId,
        intent: WorkspaceMembershipAuthorityLifecycleIntent,
        expected_revision: WorkspaceMembershipAuthoritySetRevisionId,
    ) -> AuthorizedWorkspaceMembershipAuthorityLifecycleChange | None: ...


class OfflineWorkspaceMembershipAuthorityRecoveryStore(Protocol):
    """Recover one historically authorized manager in a closed workspace."""

    def recover(
        self,
        recovery_id: WorkspaceMembershipAuthorityRecoveryId,
        target_user_id: UserId,
        workspace_id: WorkspaceId,
        expected_revision: WorkspaceMembershipAuthoritySetRevisionId,
    ) -> RecoveredWorkspaceMembershipAuthoritySet | None: ...


class AuthorizedWorkspaceMembershipChangeStore(Protocol):
    """Atomically authorize and persist one complete membership snapshot."""

    def change_membership(
        self,
        change_id: WorkspaceMembershipChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        workspace_id: WorkspaceId,
        expected_revision: WorkspaceMembershipRevisionId | None,
        status: MembershipStatus,
        permissions: frozenset[Permission],
    ) -> AuthorizedWorkspaceMembershipChange | None: ...


class OidcTrustManagementAuthorityLookup(Protocol):
    """Resolve current global OIDC-trust authority for one session actor.

    The principal identifies only the actor. Implementations must resolve the
    actor's current active state and dedicated system-wide capability from the
    system of record. No role, allow boolean, workspace, issuer, provider,
    revision, or configuration selector is accepted. ``False`` neutrally covers
    absence, inactivity, and revocation; technical inability remains distinct.
    """

    def permits_oidc_trust_management(self, principal: SessionPrincipal) -> bool: ...


class UserLifecycleManagementAuthorityLookup(Protocol):
    """Resolve current global user-lifecycle authority for one actor only."""

    def permits_user_lifecycle_management(
        self, principal: SessionPrincipal
    ) -> bool: ...


class WorkspaceLifecycleManagementAuthorityLookup(Protocol):
    """Resolve current global workspace-lifecycle authority for one actor only."""

    def permits_workspace_lifecycle_management(
        self, principal: SessionPrincipal
    ) -> bool: ...


class UserLifecycleAuthoritySetAnchor(Protocol):
    def anchor(
        self, change_id: UserLifecycleAuthorityChangeId,
        principal: SessionPrincipal,
    ) -> AnchoredUserLifecycleAuthoritySet | None: ...


class WorkspaceLifecycleAuthoritySetAnchor(Protocol):
    def anchor(
        self, change_id: WorkspaceLifecycleAuthorityChangeId,
        principal: SessionPrincipal,
    ) -> AnchoredWorkspaceLifecycleAuthoritySet | None: ...


class AuthorizedUserLifecycleAuthorityStore(Protocol):
    def change_authority(
        self,
        change_id: UserLifecycleAuthorityChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        intent: LifecycleAuthorityIntent,
        expected_revision: UserLifecycleAuthoritySetRevisionId,
    ) -> AuthorizedUserLifecycleAuthorityChange | None: ...


class AuthorizedWorkspaceLifecycleAuthorityStore(Protocol):
    def change_authority(
        self,
        change_id: WorkspaceLifecycleAuthorityChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        intent: LifecycleAuthorityIntent,
        expected_revision: WorkspaceLifecycleAuthoritySetRevisionId,
    ) -> AuthorizedWorkspaceLifecycleAuthorityChange | None: ...


class AuthorizedUserLifecycleStore(Protocol):
    """Create or transition users against the complete current user revision."""

    def create_user(
        self,
        change_id: UserLifecycleChangeId,
        principal: SessionPrincipal,
        expected_revision: UserLifecycleRevisionId,
    ) -> AuthorizedUserLifecycleChange | None: ...


class AuthorizedWorkspaceLifecycleStore(Protocol):
    """Create or terminally deactivate complete workspace lifecycle facts."""

    def create_workspace(
        self,
        change_id: WorkspaceLifecycleChangeId,
        principal: SessionPrincipal,
        initial_onboarding_manager_user_id: UserId,
        expected_revision: WorkspaceLifecycleRevisionId,
    ) -> AuthorizedWorkspaceLifecycleChange | None: ...

    def deactivate_workspace(
        self,
        change_id: WorkspaceLifecycleChangeId,
        principal: SessionPrincipal,
        target_workspace_id: WorkspaceId,
        expected_revision: WorkspaceLifecycleRevisionId,
    ) -> AuthorizedWorkspaceLifecycleChange | None: ...

    def change_user_status(
        self,
        change_id: UserLifecycleChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        intent: UserLifecycleIntent,
        expected_revision: UserLifecycleRevisionId,
    ) -> AuthorizedUserLifecycleChange | None: ...


class InitialOidcTrustAuthorityBootstrap(Protocol):
    """Grant initial global trust authority to one existing active user, once.

    The offline caller selects only the already existing internal user. No
    actor, session, role, capability, allow decision, configuration, issuer, or
    revision is accepted. ``None`` neutrally covers a closed authority inventory
    and an unknown or inactive target; technical inability remains distinct.
    """

    def bootstrap(
        self, user_id: UserId
    ) -> BootstrappedOidcTrustAuthority | None: ...


class OidcTrustAuthoritySetAnchor(Protocol):
    """Anchor the existing global bootstrap authority exactly once."""

    def anchor(
        self,
        change_id: OidcTrustAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
    ) -> AnchoredOidcTrustAuthoritySet | None: ...


class AuthorizedOidcTrustAuthorityLifecycleStore(Protocol):
    """Atomically authorize one regular global authority transition."""

    def change_authority(
        self,
        change_id: OidcTrustAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        intent: OidcTrustAuthorityLifecycleIntent,
        expected_revision: OidcTrustAuthoritySetRevisionId,
    ) -> AuthorizedOidcTrustAuthorityLifecycleChange | None: ...


class OfflineOidcTrustAuthorityRecoveryStore(Protocol):
    """Recover one historically authorized manager in the closed global scope."""

    def recover(
        self,
        recovery_id: OidcTrustAuthorityRecoveryId,
        target_user_id: UserId,
        expected_revision: OidcTrustAuthoritySetRevisionId,
    ) -> RecoveredOidcTrustAuthoritySet | None: ...


class AuthorizedOidcTrustChangeStore(Protocol):
    """Atomically authorize and persist one complete trust transition.

    The principal identifies only the actor. An exact retry of a committed
    change is resolved before current authority; reuse with different input is
    a conflict. Configuration is required for activation and rotation and must
    be absent for deactivation.
    """

    def change_trust(
        self,
        change_id: OidcTrustChangeId,
        principal: SessionPrincipal,
        kind: OidcTrustChangeKind,
        expected_revision: OidcTrustRevisionId | None,
        configuration: TrustedOidcClientConfiguration | None,
    ) -> AuthorizedOidcTrustChange | None: ...


class InitialIdentityAuthorityBootstrap(Protocol):
    """Atomically create the first user, workspace, and management authority.

    The boundary accepts no identifiers, role, permission, or allow decision.
    ``None`` means neutrally that any foundation inventory already exists and
    the one-time boundary is permanently closed. Technical inability remains
    distinct and no partial fact may survive it.
    """

    def bootstrap(self) -> BootstrappedIdentityAuthority | None: ...


class InitialIdentityLifecycleFoundationAnchor(Protocol):
    """Adopt one exact canonical pre-LQ-220 bootstrap inventory, once."""

    def anchor(self) -> AnchoredIdentityLifecycleFoundation | None: ...


class AuthorizedOnboardingDecisionStore(Protocol):
    """Atomically resolve authority and persist one immutable decision.

    The principal identifies the actor but grants nothing. The stable internal
    decision id identifies retries but grants nothing. ``None`` neutrally
    covers absent or inactive foundation facts and absent or revoked authority.
    The provisioning handle is generated and stored by the implementation.
    """

    def decide(
        self,
        decision_id: OnboardingDecisionId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
    ) -> AuthorizedOnboardingDecision | None: ...


class BrowserSessionLookup(Protocol):
    """Resolve one opaque session identifier without exposing storage details."""

    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None: ...


class ExternalIdentityLookup(Protocol):
    """Resolve one verified external identity to an internal user, read-only."""

    def get_user_id(self, identity: ExternalIdentity) -> UserId | None: ...


class ExternalIdentityAdmissionStore(Protocol):
    """Atomically consume one admission and create its first identity binding.

    The target user is taken solely from the internally stored admission; the
    caller never supplies a UserId, so a login/callback caller cannot bind an
    external identity to a freely chosen or foreign user. Admission validity,
    expiry, single-use consumption, and the first binding happen atomically. On
    success the internally determined UserId is returned; an exact repeat of the
    same completed operation is idempotent and returns the same UserId. An
    unknown, expired, or otherwise consumed admission, an identity collision, or
    a binding to a different user all fail neutrally to None, indistinguishably.
    """

    def consume_admission_and_bind(
        self,
        admission_id: IdentityAdmissionId,
        identity: ExternalIdentity,
    ) -> UserId | None: ...


class IdentityAdmissionProvisioningStore(Protocol):
    """Store exactly one new admission for one authorized onboarding decision.

    Deliberately separate from ExternalIdentityAdmissionStore: this is an
    administrative boundary reached only from an already authorized internal
    onboarding process, never from login start, the OIDC callback, or any
    runtime consumer, so the runtime store gains no administration method.

    Target user and workspace come solely from that authorized decision; the
    port creates no user, workspace, membership, or permission and accepts no
    OIDC claim or callback value as a target. It generates the returned
    IdentityAdmissionId itself and derives expiry from its own injected clock
    plus the given lifetime, so the caller can set neither. The stored
    admission starts unconsumed and unbound.

    Retry safety hangs solely on the caller's ProvisioningRequestId: the same
    handle with the same business input returns the stored IdentityAdmissionId
    unchanged, without extending expiry or reopening it, while the same handle
    with different content raises IdentityAdmissionProvisioningConflict instead
    of overwriting or provisioning twice. An unclear outcome raises
    IdentityAdmissionStoreUnavailable and is resolved by repeating with the
    same handle. Both errors are detail-free.
    """

    def provision_admission(
        self,
        request_id: ProvisioningRequestId,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
        lifetime: timedelta,
    ) -> IdentityAdmissionId: ...


class OidcLoginTransactionClaimStore(Protocol):
    """Atomically claim one pending login transaction exactly once.

    Before succeeding the store checks that the transaction exists, is still
    pending, and has not expired. It reads its own clock: the caller supplies
    neither ``now`` nor any expiry decision, and beyond the state it supplies no
    issuer, nonce, verifier, admission handle, or other transaction material.
    Success consumes or removes the pending state fail-closed and hands the
    PendingOidcLoginTransaction to the callback process exactly once; a second
    claim of the same state returns None. Unknown, expired, and already claimed
    states are indistinguishable None, revealing nothing about an admission,
    issuer, user, or transaction state.

    An existing but expired transaction returns None outwardly and its
    secret-bearing pending state is atomically removed or permanently treated as
    consumed in the same step: expected_nonce and code_verifier must not become
    available again through that state. A persistent implementation may instead
    leave a secret-free consumption proof or tombstone behind. No secrets are
    kept in an expired pending state.

    This port verifies no OIDC token and no current issuer-trust configuration.
    The successful result briefly carries the secrets needed for exactly this
    callback; their further use belongs to a later use case. A persistent
    implementation may keep a separate consumption proof or tombstone.
    """

    def claim_transaction(
        self,
        state: OidcLoginState,
    ) -> PendingOidcLoginTransaction | None: ...


class OidcLoginTransactionCreationStore(Protocol):
    """Atomically store one new pending login transaction without reusing a state.

    Success returns True and keeps exactly the given immutable record under the
    exact opaque state; neither is normalized or altered. An existing pending
    record is never overwritten, so a state that is already pending returns a
    neutral False. A state that was previously claimed, consumed, or dropped on
    expiry and is known through a consumption proof or tombstone must not be
    reused and returns the same neutral False: an old callback can therefore
    never meet a new login transaction by re-occupying its state. False does not
    distinguish a pending collision from an already used state. A persistent
    store must secure that non-reuse atomically; a later local adapter may keep
    an internal, secret-free reserved/used state set for it.

    The caller supplies no ``now``, and this port decides nothing about issuer
    trust, OIDC tokens, admission, or authorization. Ensuring the record has not
    already expired at creation time belongs to the later login-start use case.
    The store performs no automatic retry and generates no material, and no
    secrets are logged or carried in a failure result.
    """

    def add_transaction(
        self,
        state: OidcLoginState,
        transaction: PendingOidcLoginTransaction,
    ) -> bool: ...


class ActiveOidcClientConfigurationLookup(Protocol):
    """Read the one currently active OIDC client configuration, read-only.

    The method takes no argument beyond ``self``. Liquent supports exactly one
    active configuration at this boundary, so no issuer, provider, client id,
    tenant, workspace, user, host, header, query value, cookie, admission
    handle, return path, or other selector can be passed. A later HTTP boundary
    therefore cannot hand a browser-chosen provider to this port at all: the
    protection is structural, not a runtime check.

    A returned configuration is exactly the stored immutable object — not a
    copy with altered values, nothing normalized, nothing added, no secret
    attached. Holding it freezes no trust status: every login start reads the
    current configuration again, and the callback must still re-check the
    current issuer trust separately.

    ``None`` means only that no active OIDC client configuration is available
    for login right now. It never distinguishes "never configured" from
    "deactivated" or "approval revoked", and it reveals no previously
    configured issuer or client; a later transport boundary must keep that
    neutrality. The port returns no list, no deactivated configuration, no
    alternative or default fallback, and no detail reason.

    A genuine read, configuration, or infrastructure failure must not be
    silently turned into ``None``. This port defines no error type and no error
    handling of its own; a later application or transport boundary handles
    failures neutrally without faking an empty state.

    The port only reads. It activates and deactivates nothing, creates,
    updates, deletes, and rotates nothing, runs no discovery, loads no signing
    key set, performs no network call, requires no caching, and decides no
    workspace permission. Supporting several trusted issuers later needs its
    own contract and must not silently change the meaning of this method.
    """

    def get_active_configuration(
        self,
    ) -> TrustedOidcClientConfiguration | None: ...


class ActiveOidcTrustLookup(Protocol):
    """Read one active revision and configuration as an atomic snapshot."""

    def get_active_trust(self) -> ActiveOidcTrustSnapshot | None: ...


class OidcAuthorizationCodeVerifier(Protocol):
    """Redeem one authorization code and return only a verified identity.

    This is level three of the LQ-155 callback: it is reached **only after** the
    browser binding matched and the login transaction was claimed atomically
    exactly once. The single argument carries the authorization code and the
    four verification-relevant values of that already claimed transaction.

    **Success.** An ExternalIdentity is returned only when an implementation has
    completed all of the following: read the active configuration exactly once;
    found one present; matched its issuer byte for byte against the stored
    expected_issuer; redeemed the code exactly once at the configured token
    endpoint using the stored code_verifier and the stored redirect_uri
    unchanged; verified the ID token's signature under an explicitly allowed
    algorithm; taken the key solely from the configured trusted JWKS set;
    verified iss, aud, azp where several audiences are present, exp, nbf, iat,
    and nonce in full; and found a non-empty sub. The result is exactly
    ExternalIdentity(issuer, subject) and carries no token, claim, or other
    value. A successful token endpoint response is never a reason to skip one of
    these checks.

    **Business rejection.** ``None`` is the only business rejection and
    distinguishes nothing: no active configuration, an expected issuer that is
    no longer active, a refused or invalid code, a missing or invalid token, a
    signature, algorithm, key, or claim failure, an issuer, audience, azp, time,
    or nonce failure, and a missing or empty subject all look identical. It
    carries no cause and no existence information, so a caller cannot learn
    whether a configuration, identity, or subject exists.

    **Technical unavailability.** OidcVerificationUnavailable is raised instead
    when the verification could not be carried out at all — an unreadable
    configuration store, a network failure, an unreachable token endpoint or
    JWKS source, key verification that cannot be performed safely, or an
    internal adapter or library fault. An implementation must translate its
    internal failures into that neutral error rather than let one propagate that
    could carry a code, token, nonce, verifier, issuer, provider text, or
    configuration detail.

    **Consumption.** This port claims no login transaction, sees no state, and
    performs no store rollback; it cannot tell whether a transaction ever
    existed. It is called only after the atomic claim, so the transaction is
    already consumed in every outcome and stays consumed. Neither ``None`` nor
    OidcVerificationUnavailable is retryable for the same transaction — a new
    attempt needs a new login start, because a retry would be a replay path.

    The port selects no provider, accepts no issuer, tenant, client, host,
    header, cookie, or request value, reads no clock from its caller, resolves
    no identity to a UserId, consumes no admission, and creates no session. A
    returned identity means only that this external identity was fully verified
    for exactly this login transaction.
    """

    def verify_authorization_code(
        self,
        verification: OidcAuthorizationCodeVerification,
    ) -> ExternalIdentity | None: ...


class BrowserSessionLifecycle(Protocol):
    """Create, rotate, and revoke server-side browser sessions."""

    def create_session(self, principal: SessionPrincipal) -> IssuedBrowserSession: ...

    def rotate_session(
        self, session_id: SessionId
    ) -> IssuedBrowserSession | None: ...

    def revoke_session(self, session_id: SessionId) -> None: ...


class BrowserSessionCreationStore(Protocol):
    """Atomically add one new session without replacing an existing record."""

    def add_session(
        self,
        session_id: SessionId,
        record: BrowserSessionRecord,
    ) -> bool: ...


class BrowserSessionRotationStore(Protocol):
    """Atomically revoke a valid session and add a replacement bound to its principal.

    The store reads the current record, reuses its unchanged principal for the
    replacement, revokes the old record, and adds the new one in one step. The
    caller never supplies a principal, so a replacement cannot bind a foreign one.
    """

    def rotate_session(
        self,
        current_id: SessionId,
        replacement: IssuedBrowserSession,
    ) -> bool: ...


class BrowserSessionRevocationStore(Protocol):
    """Idempotently revoke one browser session without revealing its state.

    Unknown, already revoked, or expired sessions are neutral no-ops. The
    return value never signals whether a session existed or was valid.
    """

    def revoke_session(self, session_id: SessionId) -> None: ...


class BrowserSessionMaterialGenerator(Protocol):
    """Generate independent opaque material for one new browser session."""

    def new_session_id(self) -> SessionId: ...

    def new_csrf_token(self) -> str: ...
