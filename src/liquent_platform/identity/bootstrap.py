"""Result of the one-time internal identity-authority bootstrap."""

from dataclasses import dataclass, field

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.research import WorkspaceId


@dataclass(frozen=True, slots=True)
class BootstrappedIdentityAuthority:
    """Expose only the identifiers needed to complete the first login."""

    user_id: UserId = field(repr=False)
    workspace_id: WorkspaceId = field(repr=False)
    admission_id: IdentityAdmissionId = field(repr=False)
