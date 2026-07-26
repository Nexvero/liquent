"""Pure authorization decision for the first research slice."""

from collections.abc import Collection

from liquent_platform.identity.access import MembershipStatus, Permission


def permits_research(
    membership_status: MembershipStatus,
    granted_permissions: Collection[Permission],
    required_permission: Permission,
) -> bool:
    """Return whether an active member has the required research permission."""

    if membership_status is not MembershipStatus.ACTIVE:
        return False
    if required_permission is Permission.RESEARCH_READ:
        return bool(
            {Permission.RESEARCH_READ, Permission.RESEARCH_WRITE}
            & set(granted_permissions)
        )
    return Permission.RESEARCH_WRITE in granted_permissions
