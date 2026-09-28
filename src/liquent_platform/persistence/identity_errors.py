"""Neutral technical errors of the persistent external-identity store."""


class ExternalIdentityStoreUnavailable(Exception):
    """Report that the identity store could not answer, without any detail.

    Kept apart from the neutral ``None`` of a business decision: an unreachable
    database, a transaction that cannot be completed safely, a stored record
    that violates the structural invariants, and an unusable clock are all
    technical, while an unknown, expired, or already consumed admission is not.

    It holds no identity, user, workspace, admission id, provisioning handle,
    SQL, table, constraint, driver, host, port, or DSN detail, so it reveals
    nothing about what exists or how the store is built.
    """

    code = "external_identity_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class IdentityAdmissionProvisioningConflict(Exception):
    """Report that a provisioning handle was reused with different content.

    The same ProvisioningRequestId with the same business input is a retry and
    returns the stored admission id; with different content it is this contract
    violation, never resolved by overwriting the stored admission and never by
    creating a second one. Kept apart from technical unavailability: the stored
    state is intact and repeating changes nothing. It holds no handle,
    identifier, or storage detail, so it reveals neither what is stored nor
    what differed.
    """

    code = "identity_admission_provisioning_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class IdentityAdmissionStoreUnavailable(Exception):
    """Report that admission provisioning could not be completed, detail-free.

    Raised when the operation could not be carried out at all or its outcome
    stays unclear — an unreachable database, a transaction that cannot complete
    safely, an unusable clock or id generator. It is neither a business
    decision nor a contract conflict: the authorized caller resolves it by
    repeating with the same handle, so at most one admission is ever created.
    It holds no handle, identifier, or storage detail, so it reveals nothing
    about what exists or how the store is built.
    """

    code = "identity_admission_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class IdentityAuthorityStoreUnavailable(Exception):
    """Report a technically unavailable authority decision without detail."""

    code = "identity_authority_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class IdentityAuthorityBootstrapUnavailable(Exception):
    """Report technically uncertain or impossible bootstrap, detail-free."""

    code = "identity_authority_bootstrap_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OnboardingDecisionConflict(Exception):
    """Report reuse of one decision identity with different business input."""

    code = "onboarding_decision_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class OnboardingDecisionStoreUnavailable(Exception):
    """Report technically uncertain or impossible decision persistence."""

    code = "onboarding_decision_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcLoginTransactionStoreUnavailable(Exception):
    """Report technically unavailable login-transaction persistence."""

    code = "oidc_login_transaction_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class BrowserSessionStoreUnavailable(Exception):
    """Report technically unavailable browser-session persistence."""

    code = "browser_session_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcClientConfigurationStoreUnavailable(Exception):
    """Report technically unavailable OIDC configuration, detail-free."""

    code = "oidc_client_configuration_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustChangeConflict(Exception):
    """Report reuse of one change identity with different business input."""

    code = "oidc_trust_change_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustChangeStoreUnavailable(Exception):
    """Report technically uncertain trust-change persistence, detail-free."""

    code = "oidc_trust_change_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipStoreUnavailable(Exception):
    """Report technically unavailable membership resolution, detail-free."""

    code = "workspace_membership_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ResearchJobStoreUnavailable(Exception):
    """Report technically unavailable research-job persistence, detail-free."""

    code = "research_job_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ManifestHandoffRegistryUnavailable(Exception):
    """Report technically unavailable manifest-handoff registry persistence."""

    code = "manifest_handoff_registry_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipManagementAuthorityUnavailable(Exception):
    """Report technically unavailable membership-management authority."""

    code = "workspace_membership_management_authority_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipManagementBootstrapUnavailable(Exception):
    """Report technically unavailable initial management bootstrap."""

    code = "workspace_membership_management_bootstrap_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipChangeConflict(Exception):
    """Report reuse of one membership change ID with different input."""

    code = "workspace_membership_change_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipChangeStoreUnavailable(Exception):
    """Report technically uncertain membership change persistence."""

    code = "workspace_membership_change_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustAuthorityStoreUnavailable(Exception):
    """Report technically unavailable OIDC-trust authority, detail-free."""

    code = "oidc_trust_authority_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class LifecycleAuthorityStoreUnavailable(Exception):
    """Report technically unavailable lifecycle authority, detail-free."""

    code = "lifecycle_authority_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class IdentityLifecycleFoundationAnchorUnavailable(Exception):
    """Report technically uncertain lifecycle anchoring, detail-free."""

    code = "identity_lifecycle_foundation_anchor_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class LifecycleAuthoritySetConflict(Exception):
    code = "lifecycle_authority_set_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class LifecycleAuthoritySetUnavailable(Exception):
    code = "lifecycle_authority_set_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class UserLifecycleChangeConflict(Exception):
    code = "user_lifecycle_change_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class UserLifecycleChangeStoreUnavailable(Exception):
    code = "user_lifecycle_change_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceLifecycleChangeConflict(Exception):
    code = "workspace_lifecycle_change_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceLifecycleChangeStoreUnavailable(Exception):
    code = "workspace_lifecycle_change_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustAuthorityBootstrapUnavailable(Exception):
    """Report technically unavailable initial trust authority, detail-free."""

    code = "oidc_trust_authority_bootstrap_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustAuthorityAnchorConflict(Exception):
    """Report reuse of an anchor change ID with different input."""

    code = "oidc_trust_authority_anchor_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustAuthorityAnchorUnavailable(Exception):
    """Report technically uncertain global authority anchoring."""

    code = "oidc_trust_authority_anchor_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipAuthorityAnchorConflict(Exception):
    """Report reuse of a workspace anchor ID with different input."""

    code = "workspace_membership_authority_anchor_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipAuthorityAnchorUnavailable(Exception):
    """Report technically uncertain workspace authority anchoring."""

    code = "workspace_membership_authority_anchor_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustAuthorityLifecycleConflict(Exception):
    """Report reuse of a global lifecycle change ID with different input."""

    code = "oidc_trust_authority_lifecycle_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustAuthorityLifecycleUnavailable(Exception):
    """Report technically uncertain global authority lifecycle persistence."""

    code = "oidc_trust_authority_lifecycle_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipAuthorityLifecycleConflict(Exception):
    """Report reuse of a workspace lifecycle ID with different input."""

    code = "workspace_membership_authority_lifecycle_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipAuthorityLifecycleUnavailable(Exception):
    """Report technically uncertain workspace authority lifecycle persistence."""

    code = "workspace_membership_authority_lifecycle_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustAuthorityRecoveryConflict(Exception):
    """Report reuse of a global recovery ID with different input."""

    code = "oidc_trust_authority_recovery_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcTrustAuthorityRecoveryUnavailable(Exception):
    """Report technically uncertain global authority recovery."""

    code = "oidc_trust_authority_recovery_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipAuthorityRecoveryConflict(Exception):
    """Report reuse of a workspace recovery ID with different input."""

    code = "workspace_membership_authority_recovery_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceMembershipAuthorityRecoveryUnavailable(Exception):
    """Report technically uncertain workspace authority recovery."""

    code = "workspace_membership_authority_recovery_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseRegistryBootstrapConflict(Exception):
    """Report bootstrap-ID reuse with different public-key material."""

    code = "release_registry_bootstrap_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseRegistryBootstrapUnavailable(Exception):
    """Report technically uncertain release-registry bootstrap, detail-free."""

    code = "release_registry_bootstrap_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseKeyActivationConflict(Exception):
    code = "release_key_activation_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseKeyActivationUnavailable(Exception):
    code = "release_key_activation_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseRegistryProjectionUnavailable(Exception):
    code = "release_registry_projection_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseSigningConflict(Exception):
    code = "release_signing_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleaseSigningUnavailable(Exception):
    code = "release_signing_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationBootstrapConflict(Exception):
    code = "release_publication_bootstrap_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationBootstrapUnavailable(Exception):
    code = "release_publication_bootstrap_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationHandoffConflict(Exception):
    code = "release_publication_handoff_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationHandoffUnavailable(Exception):
    code = "release_publication_handoff_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationAttemptConflict(Exception):
    code = "release_publication_attempt_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationAttemptUnavailable(Exception):
    code = "release_publication_attempt_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationArtifactSourceUnavailable(Exception):
    code = "release_publication_artifact_source_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationArtifactIntegrityUnavailable(Exception):
    code = "release_publication_artifact_integrity_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationTargetInspectionUnavailable(Exception):
    code = "release_publication_target_inspection_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationCreateUnavailable(Exception):
    code = "release_publication_create_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationReconciliationUnavailable(Exception):
    code = "release_publication_reconciliation_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationReconciliationFinalizeUnavailable(Exception):
    code = "release_publication_reconciliation_finalize_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationRecoveryFinalizeUnavailable(Exception):
    code = "release_publication_recovery_finalize_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationRetryAttemptUnavailable(Exception):
    code = "release_publication_retry_attempt_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationRetryCreateUnavailable(Exception):
    code = "release_publication_retry_create_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationWorkStateUnavailable(Exception):
    code = "release_publication_work_state_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationCurrentOutcomeFinalizeUnavailable(Exception):
    code = "release_publication_current_outcome_finalize_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationExecutorRegistrationUnavailable(Exception):
    code = "release_publication_executor_registration_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)
