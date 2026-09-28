"""Stable internal identities for managed OIDC trust facts."""

from dataclasses import dataclass, field
from enum import Enum

from liquent_platform.identity.access import UserId
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)


def _require_identifier(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class OidcTrustRevisionId:
    """Non-reassignable identity of one immutable trust configuration."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "oidc trust revision id")


@dataclass(frozen=True, slots=True)
class OidcTrustChangeId:
    """Non-reusable identity of one technical trust-change decision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "oidc trust change id")


@dataclass(frozen=True, slots=True)
class BootstrappedOidcTrustAuthority:
    """The one existing internal user granted initial global trust authority."""

    user_id: UserId

    def __post_init__(self) -> None:
        _require_identifier(self.user_id, "oidc trust authority user id")


@dataclass(frozen=True, slots=True)
class ActiveOidcTrustSnapshot:
    """One atomically read active revision and its immutable configuration."""

    revision_id: OidcTrustRevisionId = field(repr=False)
    configuration: TrustedOidcClientConfiguration = field(repr=False)


class OidcTrustChangeKind(str, Enum):
    """The three complete, non-patch trust transitions."""

    ACTIVATE = "activate"
    ROTATE = "rotate"
    DEACTIVATE = "deactivate"


@dataclass(frozen=True, slots=True)
class AuthorizedOidcTrustChange:
    """One committed trust-management decision, not an authority token."""

    change_id: OidcTrustChangeId = field(repr=False)
    kind: OidcTrustChangeKind
    revision_id: OidcTrustRevisionId | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class OidcTrustAuthoritySetRevisionId:
    """Identity of one immutable complete global authority set."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "oidc trust authority set revision id")


@dataclass(frozen=True, slots=True)
class OidcTrustAuthorityLifecycleChangeId:
    """Identity of one regular global authority lifecycle decision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "oidc trust authority lifecycle change id")


@dataclass(frozen=True, slots=True)
class OidcTrustAuthorityRecoveryId:
    """Identity of one offline global authority recovery decision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "oidc trust authority recovery id")


@dataclass(frozen=True, slots=True)
class AnchoredOidcTrustAuthoritySet:
    """One committed adoption of the existing global bootstrap authority."""

    change_id: OidcTrustAuthorityLifecycleChangeId = field(repr=False)
    revision_id: OidcTrustAuthoritySetRevisionId = field(repr=False)


class OidcTrustAuthorityLifecycleIntent(str, Enum):
    """The three regular, target-specific global authority transitions."""

    GRANT = "grant"
    DEACTIVATE = "deactivate"
    REACTIVATE = "reactivate"


@dataclass(frozen=True, slots=True)
class AuthorizedOidcTrustAuthorityLifecycleChange:
    """One committed regular global authority lifecycle decision."""

    change_id: OidcTrustAuthorityLifecycleChangeId = field(repr=False)
    revision_id: OidcTrustAuthoritySetRevisionId = field(repr=False)
    target_user_id: UserId
    intent: OidcTrustAuthorityLifecycleIntent


@dataclass(frozen=True, slots=True)
class RecoveredOidcTrustAuthoritySet:
    """One committed offline recovery of historical global authority."""

    recovery_id: OidcTrustAuthorityRecoveryId = field(repr=False)
    revision_id: OidcTrustAuthoritySetRevisionId = field(repr=False)
    target_user_id: UserId
