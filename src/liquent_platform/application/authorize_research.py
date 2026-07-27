"""Application-level research authorization orchestration."""

from liquent_platform.identity.access import Permission
from liquent_platform.identity.authorization import permits_research
from liquent_platform.identity.ports import WorkspaceMembershipLookup
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal


def authorize_research(
    memberships: WorkspaceMembershipLookup,
    principal: SessionPrincipal,
    workspace_id: WorkspaceId,
    required_permission: Permission,
) -> bool:
    """Resolve one membership and evaluate the existing research policy."""

    membership = memberships.get_membership(principal.user_id, workspace_id)
    if membership is None:
        return False
    if (
        membership.user_id != principal.user_id
        or membership.workspace_id != workspace_id
    ):
        return False
    return permits_research(
        membership.status,
        membership.permissions,
        required_permission,
    )
