"""Application-level research authorization orchestration."""

from liquent_platform.identity.access import Permission, UserId
from liquent_platform.identity.authorization import permits_research
from liquent_platform.identity.ports import WorkspaceMembershipLookup
from liquent_platform.identity.research import WorkspaceId


def authorize_research(
    memberships: WorkspaceMembershipLookup,
    user_id: UserId,
    workspace_id: WorkspaceId,
    required_permission: Permission,
) -> bool:
    """Resolve one membership and evaluate the existing research policy."""

    membership = memberships.get_membership(user_id, workspace_id)
    if membership is None:
        return False
    if membership.user_id != user_id or membership.workspace_id != workspace_id:
        return False
    return permits_research(
        membership.status,
        membership.permissions,
        required_permission,
    )
