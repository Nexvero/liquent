"""Stable identities for the release-signing authority control plane."""

from dataclasses import dataclass, field
from enum import Enum
import re


_FINGERPRINT_RE = re.compile(r"SHA256:[A-Za-z0-9+/]{43}")


def _require_identifier(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ReleaseSignerAuthorityId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release signer authority id")


@dataclass(frozen=True, slots=True)
class ReleaseRegistryLifecycleAuthorityId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release registry lifecycle authority id")


@dataclass(frozen=True, slots=True)
class ReleaseSigningKeyId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release signing key id")


@dataclass(frozen=True, slots=True)
class ReleaseRegistrySetRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release registry set revision id")


@dataclass(frozen=True, slots=True)
class ReleasePolicyRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release policy revision id")


@dataclass(frozen=True, slots=True)
class ReleaseRegistryLifecycleChangeId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release registry lifecycle change id")


@dataclass(frozen=True, slots=True)
class ReleaseSigningDecisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release signing decision id")


@dataclass(frozen=True, slots=True)
class ReleaseRegistryRecoveryId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release registry recovery id")


@dataclass(frozen=True, slots=True)
class ReleaseEmergencyRevocationId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release emergency revocation id")


@dataclass(frozen=True, slots=True)
class ReleaseRegistryBootstrapId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release registry bootstrap id")


@dataclass(frozen=True, slots=True)
class ReleaseActivationReviewerId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release activation reviewer id")


@dataclass(frozen=True, slots=True)
class ReleasePromotionVerifierId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release promotion verifier id")


@dataclass(frozen=True, slots=True)
class ReleaseSigningExecutorId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "release signing executor id")


@dataclass(frozen=True, slots=True)
class ReleaseSigningPublicKey:
    fingerprint: str = field(repr=False)
    public_key: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.fingerprint) is not str or not _FINGERPRINT_RE.fullmatch(
            self.fingerprint
        ):
            raise ValueError("release signing key fingerprint is invalid")
        if (
            type(self.public_key) is not str
            or "\n" in self.public_key
            or len(self.public_key.split()) != 2
            or not self.public_key.startswith("ssh-ed25519 ")
        ):
            raise ValueError("release signing public key is invalid")


@dataclass(frozen=True, slots=True)
class BootstrappedReleaseRegistry:
    bootstrap_id: ReleaseRegistryBootstrapId = field(repr=False)
    lifecycle_authority_id: ReleaseRegistryLifecycleAuthorityId = field(repr=False)
    signer_authority_id: ReleaseSignerAuthorityId = field(repr=False)
    key_id: ReleaseSigningKeyId = field(repr=False)
    registry_revision_id: ReleaseRegistrySetRevisionId = field(repr=False)
    policy_revision_id: ReleasePolicyRevisionId = field(repr=False)


@dataclass(frozen=True, slots=True)
class ActivatedReleaseSigningKey:
    change_id: ReleaseRegistryLifecycleChangeId = field(repr=False)
    key_id: ReleaseSigningKeyId = field(repr=False)
    revision_id: ReleaseRegistrySetRevisionId = field(repr=False)
    reviewer_id: ReleaseActivationReviewerId = field(repr=False)


@dataclass(frozen=True, slots=True)
class SignedReleaseCandidate:
    decision_id: ReleaseSigningDecisionId = field(repr=False)
    signature: bytes = field(repr=False)
    evidence: bytes = field(repr=False)


class ReleaseAuthorityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ReleaseSigningKeyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ReleasePolicyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
