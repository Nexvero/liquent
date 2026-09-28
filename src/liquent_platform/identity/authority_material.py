"""Cryptographically secure internal identity-authority identifiers."""

import secrets

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.onboarding import OnboardingDecisionId
from liquent_platform.identity.lifecycle import (
    UserLifecycleChangeId,
    UserLifecycleRevisionId,
    WorkspaceLifecycleChangeId,
    WorkspaceLifecycleRevisionId,
    UserLifecycleAuthorityChangeId,
    UserLifecycleAuthoritySetRevisionId,
    WorkspaceLifecycleAuthorityChangeId,
    WorkspaceLifecycleAuthoritySetRevisionId,
)
from liquent_platform.identity.membership_management import (
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityRecoveryId,
    WorkspaceMembershipAuthoritySetRevisionId,
    WorkspaceMembershipChangeId,
    WorkspaceMembershipRevisionId,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityRecoveryId,
    OidcTrustAuthoritySetRevisionId,
    OidcTrustChangeId,
    OidcTrustRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.release_authority import (
    ReleaseEmergencyRevocationId,
    ReleaseActivationReviewerId,
    ReleasePolicyRevisionId,
    ReleasePromotionVerifierId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistryRecoveryId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningDecisionId,
    ReleaseSigningKeyId,
)
from liquent_platform.identity.release_publication import (
    ReleasePublicationBootstrapId,
    ReleasePublicationAttemptId,
    ReleasePublicationRecoveryId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationDecisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationExecutorId,
    ReleasePublicationExecutorRegistrationId,
    ReleasePublicationHandoffId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublisherAuthorityId,
)

MINIMUM_AUTHORITY_ENTROPY_BYTES = 32


class SecureIdentityAuthorityMaterialGenerator:
    """Draw independent URL-safe identifiers from operating-system randomness."""

    __slots__ = ("_entropy_bytes",)

    def __init__(self, entropy_bytes: int = MINIMUM_AUTHORITY_ENTROPY_BYTES) -> None:
        if (
            isinstance(entropy_bytes, bool)
            or not isinstance(entropy_bytes, int)
            or entropy_bytes < MINIMUM_AUTHORITY_ENTROPY_BYTES
        ):
            raise ValueError("identity authority entropy must be at least 32 bytes")
        self._entropy_bytes = entropy_bytes

    def __repr__(self) -> str:
        return "SecureIdentityAuthorityMaterialGenerator()"

    def new_user_id(self) -> UserId:
        return UserId(self._draw())

    def new_workspace_id(self) -> WorkspaceId:
        return WorkspaceId(self._draw())

    def new_release_signer_authority_id(self) -> ReleaseSignerAuthorityId:
        return ReleaseSignerAuthorityId(self._draw())

    def new_release_registry_lifecycle_authority_id(
        self,
    ) -> ReleaseRegistryLifecycleAuthorityId:
        return ReleaseRegistryLifecycleAuthorityId(self._draw())

    def new_release_signing_key_id(self) -> ReleaseSigningKeyId:
        return ReleaseSigningKeyId(self._draw())

    def new_release_registry_set_revision_id(
        self,
    ) -> ReleaseRegistrySetRevisionId:
        return ReleaseRegistrySetRevisionId(self._draw())

    def new_release_policy_revision_id(self) -> ReleasePolicyRevisionId:
        return ReleasePolicyRevisionId(self._draw())

    def new_release_registry_lifecycle_change_id(
        self,
    ) -> ReleaseRegistryLifecycleChangeId:
        return ReleaseRegistryLifecycleChangeId(self._draw())

    def new_release_signing_decision_id(self) -> ReleaseSigningDecisionId:
        return ReleaseSigningDecisionId(self._draw())

    def new_release_registry_recovery_id(self) -> ReleaseRegistryRecoveryId:
        return ReleaseRegistryRecoveryId(self._draw())

    def new_release_emergency_revocation_id(
        self,
    ) -> ReleaseEmergencyRevocationId:
        return ReleaseEmergencyRevocationId(self._draw())

    def new_release_registry_bootstrap_id(self) -> ReleaseRegistryBootstrapId:
        return ReleaseRegistryBootstrapId(self._draw())

    def new_release_activation_reviewer_id(self) -> ReleaseActivationReviewerId:
        return ReleaseActivationReviewerId(self._draw())

    def new_release_promotion_verifier_id(self) -> ReleasePromotionVerifierId:
        return ReleasePromotionVerifierId(self._draw())

    def new_release_publication_handoff_id(self) -> ReleasePublicationHandoffId:
        return ReleasePublicationHandoffId(self._draw())

    def new_release_publisher_authority_id(self) -> ReleasePublisherAuthorityId:
        return ReleasePublisherAuthorityId(self._draw())

    def new_release_publication_channel_id(self) -> ReleasePublicationChannelId:
        return ReleasePublicationChannelId(self._draw())

    def new_release_publication_channel_policy_revision_id(
        self,
    ) -> ReleasePublicationChannelPolicyRevisionId:
        return ReleasePublicationChannelPolicyRevisionId(self._draw())

    def new_release_publication_decision_id(self) -> ReleasePublicationDecisionId:
        return ReleasePublicationDecisionId(self._draw())

    def new_release_publication_provider_receipt_id(
        self,
    ) -> ReleasePublicationProviderReceiptId:
        return ReleasePublicationProviderReceiptId(self._draw())

    def new_release_publication_reassessment_id(
        self,
    ) -> ReleasePublicationReassessmentId:
        return ReleasePublicationReassessmentId(self._draw())

    def new_release_publication_bootstrap_id(
        self,
    ) -> ReleasePublicationBootstrapId:
        return ReleasePublicationBootstrapId(self._draw())

    def new_release_publication_executor_id(self) -> ReleasePublicationExecutorId:
        return ReleasePublicationExecutorId(self._draw())

    def new_release_publication_executor_registration_id(
        self,
    ) -> ReleasePublicationExecutorRegistrationId:
        return ReleasePublicationExecutorRegistrationId(self._draw())

    def new_release_publication_execution_id(self) -> ReleasePublicationExecutionId:
        return ReleasePublicationExecutionId(self._draw())

    def new_release_publication_attempt_id(self) -> ReleasePublicationAttemptId:
        return ReleasePublicationAttemptId(self._draw())

    def new_release_publication_recovery_id(self) -> ReleasePublicationRecoveryId:
        return ReleasePublicationRecoveryId(self._draw())

    def new_onboarding_decision_id(self) -> OnboardingDecisionId:
        return OnboardingDecisionId(self._draw())

    def new_provisioning_request_id(self) -> ProvisioningRequestId:
        return ProvisioningRequestId(self._draw())

    def new_identity_admission_id(self) -> IdentityAdmissionId:
        return IdentityAdmissionId(self._draw())

    def new_oidc_trust_revision_id(self) -> OidcTrustRevisionId:
        return OidcTrustRevisionId(self._draw())

    def new_oidc_trust_change_id(self) -> OidcTrustChangeId:
        return OidcTrustChangeId(self._draw())

    def new_workspace_membership_revision_id(
        self,
    ) -> WorkspaceMembershipRevisionId:
        return WorkspaceMembershipRevisionId(self._draw())

    def new_workspace_membership_change_id(self) -> WorkspaceMembershipChangeId:
        return WorkspaceMembershipChangeId(self._draw())

    def new_oidc_trust_authority_set_revision_id(
        self,
    ) -> OidcTrustAuthoritySetRevisionId:
        return OidcTrustAuthoritySetRevisionId(self._draw())

    def new_oidc_trust_authority_lifecycle_change_id(
        self,
    ) -> OidcTrustAuthorityLifecycleChangeId:
        return OidcTrustAuthorityLifecycleChangeId(self._draw())

    def new_oidc_trust_authority_recovery_id(
        self,
    ) -> OidcTrustAuthorityRecoveryId:
        return OidcTrustAuthorityRecoveryId(self._draw())

    def new_workspace_membership_authority_set_revision_id(
        self,
    ) -> WorkspaceMembershipAuthoritySetRevisionId:
        return WorkspaceMembershipAuthoritySetRevisionId(self._draw())

    def new_workspace_membership_authority_lifecycle_change_id(
        self,
    ) -> WorkspaceMembershipAuthorityLifecycleChangeId:
        return WorkspaceMembershipAuthorityLifecycleChangeId(self._draw())

    def new_workspace_membership_authority_recovery_id(
        self,
    ) -> WorkspaceMembershipAuthorityRecoveryId:
        return WorkspaceMembershipAuthorityRecoveryId(self._draw())

    def new_user_lifecycle_revision_id(self) -> UserLifecycleRevisionId:
        return UserLifecycleRevisionId(self._draw())

    def new_user_lifecycle_change_id(self) -> UserLifecycleChangeId:
        return UserLifecycleChangeId(self._draw())

    def new_workspace_lifecycle_revision_id(self) -> WorkspaceLifecycleRevisionId:
        return WorkspaceLifecycleRevisionId(self._draw())

    def new_workspace_lifecycle_change_id(self) -> WorkspaceLifecycleChangeId:
        return WorkspaceLifecycleChangeId(self._draw())

    def new_user_lifecycle_authority_set_revision_id(
        self,
    ) -> UserLifecycleAuthoritySetRevisionId:
        return UserLifecycleAuthoritySetRevisionId(self._draw())

    def new_user_lifecycle_authority_change_id(
        self,
    ) -> UserLifecycleAuthorityChangeId:
        return UserLifecycleAuthorityChangeId(self._draw())

    def new_workspace_lifecycle_authority_set_revision_id(
        self,
    ) -> WorkspaceLifecycleAuthoritySetRevisionId:
        return WorkspaceLifecycleAuthoritySetRevisionId(self._draw())

    def new_workspace_lifecycle_authority_change_id(
        self,
    ) -> WorkspaceLifecycleAuthorityChangeId:
        return WorkspaceLifecycleAuthorityChangeId(self._draw())

    def _draw(self) -> str:
        return secrets.token_urlsafe(self._entropy_bytes)
