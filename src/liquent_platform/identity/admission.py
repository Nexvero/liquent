"""Internal identity-admission types: an opaque handle and its stored record."""

from dataclasses import dataclass, field
from datetime import datetime

from liquent_platform.identity.access import UserId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.research import WorkspaceId


@dataclass(frozen=True, slots=True)
class IdentityAdmissionId:
    """An opaque handle to a previously issued internal admission.

    The value is a sensitive capability handle: it can reference a single-use
    onboarding or binding operation, so it is hidden from ``repr`` and must not
    reach logs or error diagnostics through an object representation. It stays
    available via ``.value`` for authorized internal processing.

    The value is stored verbatim: no trimming, lowercasing, or normalization.
    The object carries no admission state. Presenting this handle determines
    neither the target user nor any permission; target, validity, expiry, and
    consumption state are resolved exclusively from Liquent's internal state.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("admission id must not be empty")


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class IdentityAdmissionRecord:
    """The internally stored state of one identity admission.

    The record type itself expresses the purpose: the first-time binding of an
    external identity to an already onboarded internal user. It holds only that
    state and normalizes nothing. It decides no validity and mutates no state;
    it carries no email, claims, IdP tokens, roles, permissions, or session
    data. The target workspace only bounds the intended context and grants no
    membership, role, or permission. A consumed record keeps the exact bound
    ExternalIdentity so a later exact repeat can be recognized idempotently.
    """

    target_user_id: UserId
    target_workspace_id: WorkspaceId
    expires_at: datetime
    consumed_at: datetime | None = None
    bound_identity: ExternalIdentity | None = None

    def __post_init__(self) -> None:
        _require_aware(self.expires_at, "expires_at")
        if self.consumed_at is not None:
            _require_aware(self.consumed_at, "consumed_at")
        if (self.consumed_at is None) is not (self.bound_identity is None):
            raise ValueError("consumed_at and bound_identity must be set together")
