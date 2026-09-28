"""Resolve a current workspace only when current research-read access exists."""

from liquent_platform.application.authorize_research import authorize_research
from liquent_platform.identity.access import CurrentWorkspaceContext, Permission
from liquent_platform.identity.ports import (
    CurrentWorkspaceContextLookup,
    WorkspaceMembershipLookup,
)
from liquent_platform.identity.session import SessionPrincipal


def resolve_workspace_research_read(
    contexts: CurrentWorkspaceContextLookup,
    memberships: WorkspaceMembershipLookup,
    principal: SessionPrincipal,
) -> CurrentWorkspaceContext | None:
    """Return one current context only after a fresh research-read decision."""

    context = contexts.resolve_current_workspace(principal.user_id)
    if context is None:
        return None
    if not permits_workspace_research_read(memberships, principal, context):
        return None
    return context


def permits_workspace_research_read(
    memberships: WorkspaceMembershipLookup,
    principal: SessionPrincipal,
    context: CurrentWorkspaceContext,
) -> bool:
    """Authorize read access for one already resolved current context."""

    if context.user_id != principal.user_id:
        return False
    return authorize_research(
        memberships,
        principal,
        context.workspace_id,
        Permission.RESEARCH_READ,
    )
